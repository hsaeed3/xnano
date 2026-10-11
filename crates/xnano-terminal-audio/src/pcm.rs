//! PCM formats, conversion and lazily decoded audio files.
//!
//! Audio bytes are never cell-grid bytes: a [`Format`] states exactly how many channels, which
//! sample rate and which sample type a run of bytes uses. Everything is mixed internally as
//! stereo `f32` frames, so converting is only ever "bytes to frames" and "frames to bytes".

use std::collections::VecDeque;
use std::fs::File;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use symphonia::core::codecs::audio::{AudioDecoder, AudioDecoderOptions};
use symphonia::core::errors::Error as DecodeError;
use symphonia::core::formats::probe::Hint;
use symphonia::core::formats::{FormatOptions, FormatReader, SeekMode, SeekTo, TrackType};
use symphonia::core::io::MediaSourceStream;
use symphonia::core::meta::MetadataOptions;

use crate::TerminalAudioError;

pub type Frame = [f32; 2];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SampleType {
    F32,
    S16,
}

impl SampleType {
    pub fn name(self) -> &'static str {
        match self {
            Self::F32 => "f32le",
            Self::S16 => "s16le",
        }
    }

    fn bytes(self) -> usize {
        match self {
            Self::F32 => 4,
            Self::S16 => 2,
        }
    }
}

/// How a run of PCM bytes is laid out.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Format {
    pub sample_rate: u32,
    pub channels: u16,
    pub sample_type: SampleType,
}

impl Format {
    pub const DEFAULT: Self = Self {
        sample_rate: 44_100,
        channels: 2,
        sample_type: SampleType::F32,
    };

    pub fn bytes_per_frame(self) -> usize {
        usize::from(self.channels) * self.sample_type.bytes()
    }

    /// Frames from interleaved bytes. The byte count must be a whole number of frames.
    pub fn decode(self, bytes: &[u8]) -> Result<Vec<Frame>, String> {
        let width = self.bytes_per_frame();
        if !bytes.len().is_multiple_of(width) {
            return Err(format!(
                "{} bytes is not a whole number of {}-byte frames ({} channels of {}); return \
                 complete interleaved frames",
                bytes.len(),
                width,
                self.channels,
                self.sample_type.name()
            ));
        }
        let channels = usize::from(self.channels);
        let sample = |chunk: &[u8]| match self.sample_type {
            SampleType::F32 => f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]),
            SampleType::S16 => f32::from(i16::from_le_bytes([chunk[0], chunk[1]])) / 32768.0,
        };
        let step = self.sample_type.bytes();
        Ok(bytes
            .chunks_exact(width)
            .map(|frame| {
                let left = sample(&frame[..step]);
                let right = if channels > 1 {
                    sample(&frame[step..2 * step])
                } else {
                    left
                };
                [left, right]
            })
            .collect())
    }

    /// Interleaved bytes from frames (mono formats keep the average of both channels).
    pub fn encode(self, frames: &[Frame]) -> Vec<u8> {
        let mut bytes = Vec::with_capacity(frames.len() * self.bytes_per_frame());
        let mut push = |value: f32| match self.sample_type {
            SampleType::F32 => bytes.extend_from_slice(&value.to_le_bytes()),
            SampleType::S16 => {
                let scaled = (value.clamp(-1.0, 1.0) * 32767.0).round() as i16;
                bytes.extend_from_slice(&scaled.to_le_bytes());
            }
        };
        for frame in frames {
            if self.channels == 1 {
                push(f32::midpoint(frame[0], frame[1]));
            } else {
                push(frame[0]);
                push(frame[1]);
            }
        }
        bytes
    }
}

/// Streaming linear-interpolation sample-rate conversion.
pub struct Resampler {
    step: f64,
    position: f64,
    previous: Option<Frame>,
}

impl Resampler {
    pub fn new(input_rate: u32, output_rate: u32) -> Self {
        Self {
            step: f64::from(input_rate) / f64::from(output_rate),
            position: 0.0,
            previous: None,
        }
    }

    pub fn is_identity(&self) -> bool {
        (self.step - 1.0).abs() < f64::EPSILON
    }

    pub fn process(&mut self, input: &[Frame], output: &mut Vec<Frame>) {
        if self.is_identity() {
            output.extend_from_slice(input);
            return;
        }
        let mut sequence: Vec<Frame> = Vec::with_capacity(input.len() + 1);
        sequence.extend(self.previous);
        sequence.extend_from_slice(input);
        if sequence.len() < 2 {
            self.previous = sequence.last().copied();
            return;
        }
        let last = (sequence.len() - 1) as f64;
        while self.position < last {
            let index = self.position as usize;
            let fraction = (self.position - index as f64) as f32;
            let (a, b) = (sequence[index], sequence[index + 1]);
            output.push([
                a[0] + (b[0] - a[0]) * fraction,
                a[1] + (b[1] - a[1]) * fraction,
            ]);
            self.position += self.step;
        }
        self.position -= last;
        self.previous = sequence.last().copied();
    }

    pub fn reset(&mut self) {
        self.position = 0.0;
        self.previous = None;
    }
}

/// Where a voice's frames come from. Frames are at the player's sample rate.
pub trait FrameSource: Send {
    /// Up to `frames` frames; an empty result means the source has ended.
    fn read(&mut self, frames: usize) -> Result<Vec<Frame>, String>;

    /// Release anything the source holds.
    fn close(&mut self);
}

/// An audio file decoded packet by packet.
struct FileDecoder {
    reader: Box<dyn FormatReader>,
    decoder: Box<dyn AudioDecoder>,
    track_id: u32,
    pub sample_rate: u32,
    pub channels: usize,
    scratch: Vec<f32>,
}

fn describe(error: &DecodeError) -> String {
    error.to_string()
}

impl FileDecoder {
    fn open(path: &PathBuf) -> Result<Self, String> {
        let file = File::open(path).map_err(|error| {
            format!(
                "the audio file {} could not be opened: {error}",
                path.display()
            )
        })?;
        let stream = MediaSourceStream::new(
            Box::new(file),
            symphonia::core::io::MediaSourceStreamOptions::default(),
        );
        let mut hint = Hint::new();
        if let Some(extension) = path.extension().and_then(|extension| extension.to_str()) {
            hint.with_extension(extension);
        }
        let reader = symphonia::default::get_probe()
            .probe(
                &hint,
                stream,
                FormatOptions::default(),
                MetadataOptions::default(),
            )
            .map_err(|error| {
                format!(
                    "{} is not a supported audio file ({}); supported formats are WAV, FLAC, \
                     Ogg Vorbis, MP3 and MP4/AAC",
                    path.display(),
                    describe(&error)
                )
            })?;
        let track = reader
            .default_track(TrackType::Audio)
            .ok_or_else(|| format!("{} contains no audio track", path.display()))?;
        let parameters = track
            .codec_params
            .as_ref()
            .and_then(|parameters| parameters.audio())
            .ok_or_else(|| format!("{} has no usable audio parameters", path.display()))?;
        let decoder = symphonia::default::get_codecs()
            .make_audio_decoder(parameters, &AudioDecoderOptions::default())
            .map_err(|error| {
                format!(
                    "the audio in {} cannot be decoded: {}",
                    path.display(),
                    describe(&error)
                )
            })?;
        let sample_rate = parameters.sample_rate.unwrap_or(44_100);
        let channels = parameters
            .channels
            .as_ref()
            .map_or(2, symphonia::core::audio::Channels::count);
        let track_id = track.id;
        Ok(Self {
            reader,
            decoder,
            track_id,
            sample_rate,
            channels,
            scratch: Vec::new(),
        })
    }

    /// The next decoded packet as stereo frames, or `None` at the end of the file.
    fn next_chunk(&mut self) -> Result<Option<Vec<Frame>>, String> {
        loop {
            let packet = match self.reader.next_packet() {
                Ok(Some(packet)) => packet,
                Ok(None) => return Ok(None),
                Err(error) => return Err(describe(&error)),
            };
            if packet.track_id != self.track_id {
                continue;
            }
            match self.decoder.decode(&packet) {
                Ok(buffer) => {
                    let channels = buffer.spec().channels().count().max(1);
                    self.scratch.resize(buffer.samples_interleaved(), 0.0);
                    buffer.copy_to_slice_interleaved(&mut self.scratch);
                    let frames = self
                        .scratch
                        .chunks_exact(channels)
                        .map(|frame| {
                            let left = frame[0];
                            [left, if channels > 1 { frame[1] } else { left }]
                        })
                        .collect();
                    return Ok(Some(frames));
                }
                Err(DecodeError::IoError(_) | DecodeError::DecodeError(_)) => {}
                Err(error) => return Err(describe(&error)),
            }
        }
    }

    fn seek(&mut self, seconds: f64) -> Result<(), String> {
        let time = symphonia::core::units::Time::try_from_secs_f64(seconds.max(0.0))
            .ok_or_else(|| "the seek position is out of range".to_owned())?;
        self.reader
            .seek(
                SeekMode::Accurate,
                SeekTo::Time {
                    time,
                    track_id: Some(self.track_id),
                },
            )
            .map_err(|error| format!("seeking failed: {}", describe(&error)))?;
        self.decoder.reset();
        Ok(())
    }
}

/// A decoded file converted to a fixed output rate.
pub struct FileSource {
    decoder: FileDecoder,
    resampler: Resampler,
    output_rate: u32,
    pending: VecDeque<Frame>,
    has_ended: bool,
}

impl FileSource {
    pub fn open(path: &PathBuf, output_rate: Option<u32>) -> Result<(Self, u32, usize), String> {
        let decoder = FileDecoder::open(path)?;
        let (native_rate, channels) = (decoder.sample_rate, decoder.channels);
        let output_rate = output_rate.unwrap_or(native_rate);
        Ok((
            Self {
                resampler: Resampler::new(native_rate, output_rate),
                decoder,
                output_rate,
                pending: VecDeque::new(),
                has_ended: false,
            },
            output_rate,
            channels,
        ))
    }

    pub fn seek_to_frame(&mut self, frame: u64) -> Result<(), String> {
        self.decoder
            .seek(frame as f64 / f64::from(self.output_rate))?;
        self.pending.clear();
        self.resampler.reset();
        self.has_ended = false;
        Ok(())
    }
}

impl FrameSource for FileSource {
    fn read(&mut self, frames: usize) -> Result<Vec<Frame>, String> {
        let mut converted = Vec::new();
        while self.pending.len() < frames && !self.has_ended {
            match self.decoder.next_chunk()? {
                Some(chunk) => {
                    converted.clear();
                    self.resampler.process(&chunk, &mut converted);
                    self.pending.extend(converted.iter().copied());
                }
                None => self.has_ended = true,
            }
        }
        let take = frames.min(self.pending.len());
        Ok(self.pending.drain(..take).collect())
    }

    fn close(&mut self) {
        self.pending.clear();
        self.has_ended = true;
    }
}

/// Rendered samples played from memory.
pub struct SoundSource {
    samples: Arc<[f32]>,
    position: usize,
    resampler: Resampler,
}

impl SoundSource {
    pub fn new(samples: Arc<[f32]>, sample_rate: u32, output_rate: u32) -> Self {
        Self {
            samples,
            position: 0,
            resampler: Resampler::new(sample_rate, output_rate),
        }
    }
}

impl FrameSource for SoundSource {
    fn read(&mut self, frames: usize) -> Result<Vec<Frame>, String> {
        let end = (self.position + frames).min(self.samples.len());
        let input: Vec<Frame> = self.samples[self.position..end]
            .iter()
            .map(|&sample| [sample, sample])
            .collect();
        self.position = end;
        let mut output = Vec::with_capacity(input.len());
        self.resampler.process(&input, &mut output);
        Ok(output)
    }

    fn close(&mut self) {
        self.position = self.samples.len();
    }
}

/// A Python object that supplies frames: `format`, `read(frames)` and `close()`.
pub struct PythonSource {
    object: Py<PyAny>,
    format: Format,
    resampler: Resampler,
}

impl PythonSource {
    pub fn new(py: Python<'_>, object: Py<PyAny>, output_rate: u32) -> PyResult<Self> {
        let format = object
            .bind(py)
            .getattr("format")?
            .extract::<PyPcmFormat>()?
            .inner;
        Ok(Self {
            resampler: Resampler::new(format.sample_rate, output_rate),
            object,
            format,
        })
    }
}

impl FrameSource for PythonSource {
    fn read(&mut self, frames: usize) -> Result<Vec<Frame>, String> {
        Python::attach(|py| {
            let value = self
                .object
                .bind(py)
                .call_method1("read", (frames,))
                .map_err(|error| format!("the audio source failed: {error}"))?;
            let bytes: Vec<u8> = value
                .extract()
                .map_err(|_| "the audio source's read() must return bytes".to_owned())?;
            let input = self.format.decode(&bytes)?;
            let mut output = Vec::with_capacity(input.len());
            self.resampler.process(&input, &mut output);
            Ok(output)
        })
    }

    fn close(&mut self) {
        Python::attach(|py| {
            if let Err(error) = self.object.bind(py).call_method0("close") {
                error.write_unraisable(py, None);
            }
        });
    }
}

#[pyclass(
    name = "TerminalPCMFormat",
    module = "xnano_audio._xnano_audio",
    frozen,
    eq,
    hash,
    from_py_object
)]
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct PyPcmFormat {
    pub inner: Format,
}

#[pymethods]
impl PyPcmFormat {
    #[new]
    #[pyo3(signature = (*, sample_rate = 44_100, channels = 2, sample_type = "f32le"))]
    fn new(sample_rate: u32, channels: u16, sample_type: &str) -> PyResult<Self> {
        if !(8_000..=384_000).contains(&sample_rate) {
            return Err(PyValueError::new_err(format!(
                "sample_rate must be from 8000 to 384000 Hz, not {sample_rate}"
            )));
        }
        if !(1..=2).contains(&channels) {
            return Err(PyValueError::new_err(format!(
                "channels must be 1 (mono) or 2 (stereo), not {channels}"
            )));
        }
        let sample_type = match sample_type {
            "f32le" => SampleType::F32,
            "s16le" => SampleType::S16,
            other => {
                return Err(PyValueError::new_err(format!(
                    "\"{other}\" is not a sample type; use \"f32le\" or \"s16le\""
                )));
            }
        };
        Ok(Self {
            inner: Format {
                sample_rate,
                channels,
                sample_type,
            },
        })
    }

    #[getter]
    fn sample_rate(&self) -> u32 {
        self.inner.sample_rate
    }

    #[getter]
    fn channels(&self) -> u16 {
        self.inner.channels
    }

    #[getter]
    fn sample_type(&self) -> &'static str {
        self.inner.sample_type.name()
    }

    #[getter]
    fn bytes_per_frame(&self) -> usize {
        self.inner.bytes_per_frame()
    }

    fn __repr__(&self) -> String {
        format!(
            "TerminalPCMFormat(sample_rate={}, channels={}, sample_type='{}')",
            self.inner.sample_rate,
            self.inner.channels,
            self.inner.sample_type.name()
        )
    }
}

/// A lazily decoded audio file.
#[pyclass(
    name = "TerminalAudioStream",
    module = "xnano_audio._xnano_audio",
    unsendable
)]
pub struct PyAudioStream {
    pub source: Arc<Mutex<Option<FileSource>>>,
    format: Format,
}

#[pymethods]
impl PyAudioStream {
    #[classmethod]
    #[pyo3(signature = (path, *, format = None))]
    fn open(
        _cls: &Bound<'_, pyo3::types::PyType>,
        py: Python<'_>,
        path: PathBuf,
        format: Option<PyPcmFormat>,
    ) -> PyResult<Self> {
        let (source, rate, channels) = py
            .detach(|| FileSource::open(&path, format.map(|format| format.inner.sample_rate)))
            .map_err(TerminalAudioError::new_err)?;
        let format = format.map_or(
            Format {
                sample_rate: rate,
                channels: channels.clamp(1, 2) as u16,
                sample_type: SampleType::F32,
            },
            |format| format.inner,
        );
        Ok(Self {
            source: Arc::new(Mutex::new(Some(source))),
            format,
        })
    }

    #[getter]
    fn format(&self) -> PyPcmFormat {
        PyPcmFormat { inner: self.format }
    }

    #[getter]
    fn is_closed(&self) -> bool {
        self.source.lock().map_or(true, |source| source.is_none())
    }

    fn read<'py>(&self, py: Python<'py>, frames: usize) -> PyResult<Bound<'py, PyBytes>> {
        let mut guard = self
            .source
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let Some(source) = guard.as_mut() else {
            return Err(TerminalAudioError::new_err(
                "the audio stream is closed; open it again with TerminalAudioStream.open",
            ));
        };
        let decoded = py
            .detach(|| source.read(frames))
            .map_err(TerminalAudioError::new_err)?;
        Ok(PyBytes::new(py, &self.format.encode(&decoded)))
    }

    fn seek(&self, py: Python<'_>, frame: u64) -> PyResult<()> {
        let mut guard = self
            .source
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        let Some(source) = guard.as_mut() else {
            return Err(TerminalAudioError::new_err(
                "the audio stream is closed; open it again with TerminalAudioStream.open",
            ));
        };
        py.detach(|| source.seek_to_frame(frame))
            .map_err(TerminalAudioError::new_err)
    }

    fn close(&self) {
        if let Some(mut source) = self
            .source
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
            .take()
        {
            source.close();
        }
    }

    fn __enter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    #[pyo3(signature = (exception_type = None, exception_value = None, traceback = None))]
    fn __exit__(
        &self,
        exception_type: Option<&Bound<'_, PyAny>>,
        exception_value: Option<&Bound<'_, PyAny>>,
        traceback: Option<&Bound<'_, PyAny>>,
    ) -> bool {
        let _ = (exception_type, exception_value, traceback);
        self.close();
        false
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyPcmFormat>()?;
    m.add_class::<PyAudioStream>()
}
