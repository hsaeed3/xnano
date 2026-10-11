//! Buffered streaming playback: voices, a mixer and an optional output device.
//!
//! A producer worker reads and decodes each source ahead of time into a per-voice buffer.
//! The device callback only mixes buffers that are already in memory, so Python code never
//! runs on the audio thread. When a buffer runs dry the callback plays silence and counts an
//! underrun. The `null` backend has no device and no worker: `advance` fills and mixes
//! synchronously, which makes playback deterministic for tests.

use std::collections::VecDeque;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread::JoinHandle;
use std::time::{Duration, Instant};

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

use crate::TerminalAudioError;
use crate::pcm::{
    Format, Frame, FrameSource, PyAudioStream, PyPcmFormat, PythonSource, SoundSource,
};
use crate::synth::PySound;

const CHUNK_FRAMES: usize = 2048;

fn lock<T>(mutex: &Mutex<T>) -> std::sync::MutexGuard<'_, T> {
    mutex
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}

struct VoiceState {
    volume: f32,
    target: f32,
    step: f32,
    pan: f32,
    is_paused: bool,
    has_source_ended: bool,
    is_finished: bool,
    should_finish_at_silence: bool,
    position: u64,
    underruns: u64,
    last_error: Option<String>,
}

/// One independently controlled playback.
pub struct Voice {
    ring: Mutex<VecDeque<Frame>>,
    state: Mutex<VoiceState>,
    source: Mutex<Option<Box<dyn FrameSource>>>,
    should_close_source: bool,
}

impl Voice {
    fn new(
        source: Box<dyn FrameSource>,
        volume: f32,
        pan: f32,
        should_close_source: bool,
    ) -> Arc<Self> {
        Arc::new(Self {
            ring: Mutex::new(VecDeque::new()),
            state: Mutex::new(VoiceState {
                volume,
                target: volume,
                step: 0.0,
                pan,
                is_paused: false,
                has_source_ended: false,
                is_finished: false,
                should_finish_at_silence: false,
                position: 0,
                underruns: 0,
                last_error: None,
            }),
            source: Mutex::new(Some(source)),
            should_close_source,
        })
    }

    fn close_source(&self) {
        if self.should_close_source
            && let Some(mut source) = lock(&self.source).take()
        {
            source.close();
        }
        lock(&self.source).take();
    }

    /// Read ahead until `lookahead` frames are buffered.
    fn fill(&self, lookahead: usize) {
        loop {
            {
                let state = lock(&self.state);
                if state.has_source_ended || state.is_finished {
                    return;
                }
            }
            if lock(&self.ring).len() >= lookahead {
                return;
            }
            let taken = lock(&self.source).take();
            let Some(mut source) = taken else {
                lock(&self.state).has_source_ended = true;
                return;
            };
            let result = source.read(CHUNK_FRAMES);
            *lock(&self.source) = Some(source);
            match result {
                Ok(frames) if frames.is_empty() => {
                    lock(&self.state).has_source_ended = true;
                    return;
                }
                Ok(frames) => lock(&self.ring).extend(frames),
                Err(message) => {
                    let mut state = lock(&self.state);
                    state.last_error = Some(message);
                    state.has_source_ended = true;
                    return;
                }
            }
        }
    }

    /// Add this voice's next `output.len()` frames into `output`.
    fn mix_into(&self, output: &mut [Frame]) {
        let Ok(mut state) = self.state.try_lock() else {
            return;
        };
        if state.is_paused || state.is_finished {
            return;
        }
        let Ok(mut ring) = self.ring.try_lock() else {
            return;
        };
        for slot in output.iter_mut() {
            if state.volume != state.target {
                let next = state.volume + state.step;
                state.volume = if (state.step >= 0.0 && next >= state.target)
                    || (state.step < 0.0 && next <= state.target)
                {
                    state.target
                } else {
                    next
                };
            }
            if state.should_finish_at_silence && state.volume <= 0.0 {
                state.is_finished = true;
                ring.clear();
                break;
            }
            let Some(frame) = ring.pop_front() else {
                if state.has_source_ended {
                    state.is_finished = true;
                } else {
                    state.underruns += 1;
                }
                break;
            };
            let left = state.volume * (1.0 - state.pan).min(1.0);
            let right = state.volume * (1.0 + state.pan).min(1.0);
            slot[0] += frame[0] * left;
            slot[1] += frame[1] * right;
            state.position += 1;
        }
    }
}

/// State shared by the player object, its worker and the device callback.
pub struct Shared {
    format: Format,
    lookahead_frames: usize,
    voices: Mutex<Vec<Arc<Voice>>>,
    position: AtomicU64,
    is_closed: AtomicBool,
}

impl Shared {
    fn produce(&self) {
        let voices: Vec<Arc<Voice>> = lock(&self.voices).clone();
        for voice in voices {
            voice.fill(self.lookahead_frames);
        }
    }

    fn mix(&self, output: &mut [Frame]) {
        for slot in output.iter_mut() {
            *slot = [0.0, 0.0];
        }
        let Ok(voices) = self.voices.try_lock() else {
            return;
        };
        for voice in voices.iter() {
            voice.mix_into(output);
        }
        drop(voices);
        for slot in output.iter_mut() {
            slot[0] = slot[0].clamp(-1.0, 1.0);
            slot[1] = slot[1].clamp(-1.0, 1.0);
        }
        self.position
            .fetch_add(output.len() as u64, Ordering::SeqCst);
    }

    fn prune(&self) {
        let mut voices = lock(&self.voices);
        voices.retain(|voice| {
            let finished = lock(&voice.state).is_finished;
            if finished {
                voice.close_source();
            }
            !finished
        });
    }
}

#[cfg(feature = "playback")]
mod output {
    use std::sync::Arc;

    use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
    use cpal::{SampleFormat, Stream, StreamConfig};
    use pyo3::prelude::*;

    use super::{Frame, Shared};
    use crate::pcm::Format;
    use crate::{audio_error, unavailable_error};

    pub struct DeviceStream {
        _stream: Stream,
    }

    pub fn open(shared: &Arc<Shared>, requested: Option<Format>) -> PyResult<(DeviceStream, u32)> {
        crate::platform::silence_library_messages();
        let device = cpal::default_host()
            .default_output_device()
            .ok_or_else(|| {
                unavailable_error(
                    "no audio output device is available; connect one, use backend=\"null\" for \
                 silent deterministic playback, or test with detect_audio_capabilities() first",
                )
            })?;
        let wanted_rate = shared.format.sample_rate;
        let exact = device
            .supported_output_configs()
            .ok()
            .and_then(|mut configs| {
                configs
                    .find(|range| {
                        range.channels() == 2
                            && range.min_sample_rate() <= wanted_rate
                            && wanted_rate <= range.max_sample_rate()
                    })
                    .map(|range| range.with_sample_rate(wanted_rate))
            });
        let supported = match exact {
            Some(config) => config,
            None if requested.is_some() => {
                return Err(unavailable_error(format!(
                    "the output device cannot play stereo audio at {wanted_rate} Hz; pass a \
                     TerminalPCMFormat with a rate it supports, or omit the format to use the \
                     device's own"
                )));
            }
            None => device.default_output_config().map_err(audio_error)?,
        };
        let config: StreamConfig = supported.config();
        let channels = usize::from(config.channels);
        let rate = config.sample_rate;
        let on_error = |_error: cpal::Error| {};
        let callback_shared = Arc::clone(shared);
        let mut scratch: Vec<Frame> = Vec::new();
        macro_rules! build {
            ($type:ty, $convert:expr) => {{
                let convert = $convert;
                device.build_output_stream(
                    config,
                    move |data: &mut [$type], _| {
                        let frames = data.len() / channels.max(1);
                        scratch.resize(frames, [0.0, 0.0]);
                        callback_shared.mix(&mut scratch);
                        for (index, frame) in scratch.iter().enumerate() {
                            for channel in 0..channels {
                                let value = if channel < 2 { frame[channel] } else { 0.0 };
                                data[index * channels + channel] = convert(value);
                            }
                        }
                    },
                    on_error,
                    None,
                )
            }};
        }
        let stream = match supported.sample_format() {
            SampleFormat::F32 => build!(f32, |value: f32| value),
            SampleFormat::I16 => build!(i16, |value: f32| (value * 32767.0) as i16),
            SampleFormat::U16 => build!(u16, |value: f32| ((value * 32767.0) + 32768.0) as u16),
            other => {
                return Err(unavailable_error(format!(
                    "the output device uses the {other:?} sample format, which is not supported"
                )));
            }
        }
        .map_err(audio_error)?;
        stream.play().map_err(audio_error)?;
        Ok((DeviceStream { _stream: stream }, rate))
    }
}

#[cfg(not(feature = "playback"))]
mod output {
    use std::sync::Arc;

    use pyo3::prelude::*;

    use super::Shared;
    use crate::pcm::Format;
    use crate::unavailable_error;

    pub enum DeviceStream {}

    pub fn open(
        _shared: &Arc<Shared>,
        _requested: Option<Format>,
    ) -> PyResult<(DeviceStream, u32)> {
        Err(unavailable_error(crate::BUILT_WITHOUT_DEVICES))
    }
}

/// One independently controlled voice or stream.
#[pyclass(name = "TerminalPlayback", module = "xnano_audio._xnano_audio", frozen)]
pub struct PyPlayback {
    voice: Arc<Voice>,
    shared: Arc<Shared>,
}

fn check_volume(volume: f32) -> PyResult<f32> {
    if !volume.is_finite() {
        return Err(PyValueError::new_err(format!(
            "volume must be a finite number between 0.0 and 1.0, got {volume}"
        )));
    }
    Ok(volume.clamp(0.0, 1.0))
}

fn check_pan(pan: f32) -> PyResult<f32> {
    if !(-1.0..=1.0).contains(&pan) {
        return Err(PyValueError::new_err(format!(
            "pan must be between -1.0 (left) and 1.0 (right), got {pan}"
        )));
    }
    Ok(pan)
}

impl PyPlayback {
    fn ramp(&self, target: f32, seconds: f64) {
        let mut state = lock(&self.voice.state);
        state.target = target;
        let frames = (seconds * f64::from(self.shared.format.sample_rate)).max(1.0);
        state.step = ((f64::from(target) - f64::from(state.volume)) / frames) as f32;
        if seconds <= 0.0 {
            state.volume = target;
        }
    }
}

#[pymethods]
impl PyPlayback {
    #[getter]
    fn is_playing(&self) -> bool {
        let state = lock(&self.voice.state);
        !state.is_finished && !state.is_paused
    }

    #[getter]
    fn is_paused(&self) -> bool {
        lock(&self.voice.state).is_paused
    }

    // The volume reports the level the voice is heading to, not the instantaneous gain.
    #[allow(clippy::misnamed_getters)]
    #[getter]
    fn volume(&self) -> f32 {
        lock(&self.voice.state).target
    }

    #[setter]
    fn set_volume(&self, value: f32) -> PyResult<()> {
        self.ramp(check_volume(value)?, 0.005);
        Ok(())
    }

    #[getter]
    fn pan(&self) -> f32 {
        lock(&self.voice.state).pan
    }

    #[setter]
    fn set_pan(&self, value: f32) -> PyResult<()> {
        lock(&self.voice.state).pan = check_pan(value)?;
        Ok(())
    }

    #[getter]
    fn position_frames(&self) -> u64 {
        lock(&self.voice.state).position
    }

    #[getter]
    fn buffered_frames(&self) -> usize {
        lock(&self.voice.ring).len()
    }

    #[getter]
    fn underruns(&self) -> u64 {
        lock(&self.voice.state).underruns
    }

    #[getter]
    fn last_error(&self) -> Option<String> {
        lock(&self.voice.state).last_error.clone()
    }

    fn pause(&self) {
        lock(&self.voice.state).is_paused = true;
    }

    fn resume(&self) {
        lock(&self.voice.state).is_paused = false;
    }

    #[pyo3(signature = (volume, *, seconds))]
    fn fade_to(&self, volume: f32, seconds: f64) -> PyResult<()> {
        if !seconds.is_finite() || seconds < 0.0 {
            return Err(PyValueError::new_err(format!(
                "seconds must be zero or more, got {seconds}"
            )));
        }
        self.ramp(check_volume(volume)?, seconds);
        Ok(())
    }

    #[pyo3(signature = (*, fade_seconds = 0.0))]
    fn stop(&self, fade_seconds: f64) -> PyResult<()> {
        if !fade_seconds.is_finite() || fade_seconds < 0.0 {
            return Err(PyValueError::new_err(format!(
                "fade_seconds must be zero or more, got {fade_seconds}"
            )));
        }
        if fade_seconds == 0.0 {
            lock(&self.voice.state).is_finished = true;
            lock(&self.voice.ring).clear();
            self.voice.close_source();
        } else {
            self.ramp(0.0, fade_seconds);
            lock(&self.voice.state).should_finish_at_silence = true;
        }
        Ok(())
    }
}

/// Owns the device for buffered streams and measures time in output frames.
#[pyclass(
    name = "TerminalStreamingAudioPlayer",
    module = "xnano_audio._xnano_audio",
    unsendable
)]
pub struct PyStreamingPlayer {
    shared: Arc<Shared>,
    backend_is_null: bool,
    #[cfg_attr(not(feature = "playback"), allow(dead_code))]
    stream: Option<output::DeviceStream>,
    worker: Option<JoinHandle<()>>,
    should_stop_worker: Arc<AtomicBool>,
}

#[pymethods]
impl PyStreamingPlayer {
    #[new]
    #[pyo3(signature = (*, format = None, lookahead_milliseconds = 300, backend = "default"))]
    fn new(
        format: Option<PyPcmFormat>,
        lookahead_milliseconds: u32,
        backend: &str,
    ) -> PyResult<Self> {
        let backend_is_null = match backend {
            "default" => false,
            "null" => true,
            other => {
                return Err(PyValueError::new_err(format!(
                    "\"{other}\" is not a backend; use \"default\" or \"null\""
                )));
            }
        };
        if !(10..=10_000).contains(&lookahead_milliseconds) {
            return Err(PyValueError::new_err(format!(
                "lookahead_milliseconds must be from 10 to 10000, got {lookahead_milliseconds}"
            )));
        }
        let requested = format.map(|format| format.inner);
        let mut chosen = requested.unwrap_or(Format::DEFAULT);
        let build = |chosen: Format| {
            Arc::new(Shared {
                format: chosen,
                lookahead_frames: (u64::from(chosen.sample_rate)
                    * u64::from(lookahead_milliseconds)
                    / 1000) as usize,
                voices: Mutex::new(Vec::new()),
                position: AtomicU64::new(0),
                is_closed: AtomicBool::new(false),
            })
        };
        let mut shared = build(chosen);
        let mut stream = None;
        if !backend_is_null {
            let (opened, rate) = output::open(&shared, requested)?;
            if rate != chosen.sample_rate {
                chosen.sample_rate = rate;
                shared = build(chosen);
                // The callback captured the first state; reopen on the corrected rate.
                drop(opened);
                let (reopened, _) = output::open(&shared, Some(chosen))?;
                stream = Some(reopened);
            } else {
                stream = Some(opened);
            }
        }
        let should_stop_worker = Arc::new(AtomicBool::new(false));
        let worker = if backend_is_null {
            None
        } else {
            let (state, stop) = (Arc::clone(&shared), Arc::clone(&should_stop_worker));
            std::thread::Builder::new()
                .name("xnano-audio-producer".into())
                .spawn(move || {
                    while !stop.load(Ordering::SeqCst) {
                        state.produce();
                        state.prune();
                        std::thread::sleep(Duration::from_millis(5));
                    }
                })
                .ok()
        };
        Ok(Self {
            shared,
            backend_is_null,
            stream,
            worker,
            should_stop_worker,
        })
    }

    #[getter]
    fn format(&self) -> PyPcmFormat {
        PyPcmFormat {
            inner: self.shared.format,
        }
    }

    #[getter]
    fn is_closed(&self) -> bool {
        self.shared.is_closed.load(Ordering::SeqCst)
    }

    #[getter]
    fn sample_position(&self) -> u64 {
        self.shared.position.load(Ordering::SeqCst)
    }

    #[pyo3(signature = (source, *, volume = 1.0, pan = 0.0, should_close_source = true))]
    fn play_stream(
        &self,
        py: Python<'_>,
        source: &Bound<'_, PyAny>,
        volume: f32,
        pan: f32,
        should_close_source: bool,
    ) -> PyResult<PyPlayback> {
        self.check_open("play a stream")?;
        let volume = check_volume(volume)?;
        let pan = check_pan(pan)?;
        let rate = self.shared.format.sample_rate;
        let boxed: Box<dyn FrameSource> = if let Ok(stream) =
            source.extract::<PyRef<'_, PyAudioStream>>()
        {
            let shared_file = Arc::clone(&stream.source);
            Box::new(SharedFile { file: shared_file })
        } else {
            if !source.hasattr("read")? || !source.hasattr("format")? {
                return Err(PyValueError::new_err(
                    "an audio source needs a `format` (TerminalPCMFormat), `read(frames)` returning bytes, \
                     and `close()`; use TerminalAudioStream.open(path) for files",
                ));
            }
            Box::new(PythonSource::new(py, source.clone().unbind(), rate)?)
        };
        Ok(self.start(boxed, volume, pan, should_close_source))
    }

    #[pyo3(signature = (sound, *, volume = 1.0, pan = 0.0))]
    fn play_sound(&self, sound: &PySound, volume: f32, pan: f32) -> PyResult<PyPlayback> {
        self.check_open("play a sound")?;
        let source = SoundSource::new(
            Arc::clone(&sound.samples),
            sound.sample_rate,
            self.shared.format.sample_rate,
        );
        Ok(self.start(
            Box::new(source),
            check_volume(volume)?,
            check_pan(pan)?,
            true,
        ))
    }

    #[pyo3(signature = (outgoing, incoming, *, seconds = 3.0))]
    fn crossfade(
        &self,
        outgoing: &PyPlayback,
        incoming: &PyPlayback,
        seconds: f64,
    ) -> PyResult<()> {
        self.check_open("crossfade")?;
        let target = lock(&incoming.voice.state).target;
        {
            let mut state = lock(&incoming.voice.state);
            state.volume = 0.0;
        }
        incoming.ramp(target, seconds);
        outgoing.ramp(0.0, seconds);
        lock(&outgoing.voice.state).should_finish_at_silence = true;
        Ok(())
    }

    fn advance<'py>(&self, py: Python<'py>, frames: usize) -> PyResult<Bound<'py, PyBytes>> {
        self.check_open("advance")?;
        if !self.backend_is_null {
            return Err(TerminalAudioError::new_err(
                "advance() only works with backend=\"null\"; a live device consumes audio on its own",
            ));
        }
        let mut output = vec![[0.0; 2]; frames];
        let mut done = 0;
        while done < frames {
            let chunk = (frames - done).min(CHUNK_FRAMES);
            self.shared.produce();
            self.shared.mix(&mut output[done..done + chunk]);
            self.shared.prune();
            done += chunk;
        }
        Ok(PyBytes::new(py, &self.shared.format.encode(&output)))
    }

    #[pyo3(signature = (*, fade_seconds = 0.04, timeout_seconds = 0.25))]
    fn close(&mut self, py: Python<'_>, fade_seconds: f64, timeout_seconds: f64) -> PyResult<()> {
        if self.shared.is_closed.swap(true, Ordering::SeqCst) {
            return Ok(());
        }
        let voices: Vec<Arc<Voice>> = lock(&self.shared.voices).clone();
        if !self.backend_is_null && fade_seconds > 0.0 {
            for voice in &voices {
                let playback = PyPlayback {
                    voice: Arc::clone(voice),
                    shared: Arc::clone(&self.shared),
                };
                playback.ramp(0.0, fade_seconds);
                lock(&voice.state).should_finish_at_silence = true;
            }
            let deadline = Instant::now() + Duration::from_secs_f64(timeout_seconds.max(0.0));
            py.detach(|| {
                while Instant::now() < deadline
                    && voices.iter().any(|voice| !lock(&voice.state).is_finished)
                {
                    std::thread::sleep(Duration::from_millis(5));
                }
            });
        }
        // Stop the device before releasing what its callback reads.
        self.stream = None;
        self.should_stop_worker.store(true, Ordering::SeqCst);
        if let Some(worker) = self.worker.take() {
            py.detach(|| {
                let _ = worker.join();
            });
        }
        for voice in &voices {
            lock(&voice.state).is_finished = true;
            voice.close_source();
        }
        lock(&self.shared.voices).clear();
        Ok(())
    }

    fn __enter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    #[pyo3(signature = (exception_type = None, exception_value = None, traceback = None))]
    fn __exit__(
        &mut self,
        py: Python<'_>,
        exception_type: Option<&Bound<'_, PyAny>>,
        exception_value: Option<&Bound<'_, PyAny>>,
        traceback: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<bool> {
        let _ = (exception_type, exception_value, traceback);
        self.close(py, 0.04, 0.25)?;
        Ok(false)
    }
}

/// A file source shared with the `TerminalAudioStream` object that opened it.
struct SharedFile {
    file: Arc<Mutex<Option<crate::pcm::FileSource>>>,
}

impl FrameSource for SharedFile {
    fn read(&mut self, frames: usize) -> Result<Vec<Frame>, String> {
        match lock(&self.file).as_mut() {
            Some(file) => file.read(frames),
            None => Ok(Vec::new()),
        }
    }

    fn close(&mut self) {
        if let Some(mut file) = lock(&self.file).take() {
            file.close();
        }
    }
}

impl PyStreamingPlayer {
    fn check_open(&self, action: &str) -> PyResult<()> {
        if self.shared.is_closed.load(Ordering::SeqCst) {
            return Err(TerminalAudioError::new_err(format!(
                "cannot {action}: the player is closed; create a new TerminalStreamingAudioPlayer"
            )));
        }
        Ok(())
    }

    fn start(
        &self,
        source: Box<dyn FrameSource>,
        volume: f32,
        pan: f32,
        should_close_source: bool,
    ) -> PyPlayback {
        let voice = Voice::new(source, volume, pan, should_close_source);
        // Prime the buffer so playback can start without waiting for the worker.
        voice.fill(self.shared.lookahead_frames.min(CHUNK_FRAMES * 2));
        lock(&self.shared.voices).push(Arc::clone(&voice));
        PyPlayback {
            voice,
            shared: Arc::clone(&self.shared),
        }
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyPlayback>()?;
    m.add_class::<PyStreamingPlayer>()?;
    Ok(())
}
