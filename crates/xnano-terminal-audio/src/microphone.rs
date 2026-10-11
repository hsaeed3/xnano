//! Microphone capture: a cpal input stream that tracks the input level.
//!
//! Audio stays on the audio thread; Python only reads levels, so the GIL is
//! never involved in capture. Stream errors are recorded and reported through
//! `last_error` instead of being written to stderr, which would corrupt a
//! running terminal interface.

use std::collections::VecDeque;
use std::sync::{Arc, Mutex};

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

/// Most levels kept in the history, one per audio callback.
const HISTORY_CAPACITY: usize = 4096;

/// Levels shared between the audio thread and Python.
#[derive(Default)]
struct LevelState {
    current: f32,
    peak: f32,
    history: VecDeque<f32>,
    last_error: Option<String>,
}

impl LevelState {
    #[cfg_attr(not(feature = "playback"), allow(dead_code))]
    fn publish(&mut self, level: f32) {
        self.current = level;
        self.peak = self.peak.max(level);
        if self.history.len() == HISTORY_CAPACITY {
            self.history.pop_front();
        }
        self.history.push_back(level);
    }
}

type SharedLevels = Arc<Mutex<LevelState>>;

/// RMS of one callback's worth of samples, already normalized to `-1.0..=1.0`.
#[cfg_attr(not(feature = "playback"), allow(dead_code))]
fn root_mean_square(samples: impl Iterator<Item = f32>) -> f32 {
    let (sum, count) = samples.fold((0.0_f32, 0_u32), |(sum, count), value| {
        (sum + value * value, count + 1)
    });
    if count == 0 {
        0.0
    } else {
        (sum / count as f32).sqrt()
    }
}

#[cfg(feature = "playback")]
mod device {
    use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
    use cpal::{SampleFormat, Stream};
    use pyo3::prelude::*;

    use super::{SharedLevels, root_mean_square};
    use crate::{audio_error, unavailable_error};

    pub struct InputStream {
        _stream: Stream,
        pub sample_rate: u32,
        pub channels: u16,
    }

    /// Never blocks the audio thread: a level is skipped while Python reads.
    fn publish(levels: &SharedLevels, value: f32) {
        if let Ok(mut state) = levels.try_lock() {
            state.publish(value);
        }
    }

    pub fn open(levels: &SharedLevels) -> PyResult<InputStream> {
        crate::platform::silence_library_messages();
        let device = cpal::default_host().default_input_device().ok_or_else(|| {
            unavailable_error(
                "no microphone (audio input device) is available; connect one, or use \
                 detect_audio_capabilities() to check before opening TerminalMicrophone",
            )
        })?;
        let supported = device.default_input_config().map_err(|error| {
            unavailable_error(format!(
                "the microphone could not report its format ({error}); check that it is \
                 connected and that this application has permission to use it"
            ))
        })?;
        let config = supported.config();
        let errors = SharedLevels::clone(levels);
        let on_error = move |error: cpal::Error| {
            if let Ok(mut state) = errors.lock() {
                state.last_error = Some(error.to_string());
            }
        };

        let shared = SharedLevels::clone(levels);
        let stream = match supported.sample_format() {
            SampleFormat::F32 => device.build_input_stream(
                config,
                move |data: &[f32], _| publish(&shared, root_mean_square(data.iter().copied())),
                on_error,
                None,
            ),
            SampleFormat::I16 => device.build_input_stream(
                config,
                move |data: &[i16], _| {
                    publish(
                        &shared,
                        root_mean_square(data.iter().map(|&value| f32::from(value) / 32768.0)),
                    );
                },
                on_error,
                None,
            ),
            SampleFormat::U16 => device.build_input_stream(
                config,
                move |data: &[u16], _| {
                    publish(
                        &shared,
                        root_mean_square(
                            data.iter()
                                .map(|&value| (f32::from(value) - 32768.0) / 32768.0),
                        ),
                    );
                },
                on_error,
                None,
            ),
            other => {
                return Err(unavailable_error(format!(
                    "the microphone uses the {other:?} sample format, which is not supported; \
                     supported formats are 32-bit float, 16-bit signed and 16-bit unsigned"
                )));
            }
        }
        .map_err(audio_error)?;
        stream.play().map_err(audio_error)?;
        Ok(InputStream {
            _stream: stream,
            sample_rate: config.sample_rate,
            channels: config.channels,
        })
    }

    /// Whether the default input device exists and reports a usable format.
    pub fn is_input_available() -> bool {
        crate::platform::silence_library_messages();
        cpal::default_host()
            .default_input_device()
            .is_some_and(|device| device.default_input_config().is_ok())
    }
}

#[cfg(not(feature = "playback"))]
mod device {
    use pyo3::prelude::*;

    use super::SharedLevels;
    use crate::unavailable_error;

    pub enum InputStream {}

    impl InputStream {
        pub fn sample_rate(&self) -> u32 {
            match *self {}
        }

        pub fn channels(&self) -> u16 {
            match *self {}
        }
    }

    pub fn open(_levels: &SharedLevels) -> PyResult<InputStream> {
        Err(unavailable_error(crate::BUILT_WITHOUT_DEVICES))
    }

    pub fn is_input_available() -> bool {
        false
    }
}

pub use device::is_input_available;

/// Captures the default input device and reports its level.
#[pyclass(
    name = "TerminalMicrophone",
    module = "xnano_audio._xnano_audio",
    unsendable
)]
pub struct PyMicrophone {
    stream: Option<device::InputStream>,
    levels: SharedLevels,
    sample_rate: u32,
    channels: u16,
}

impl PyMicrophone {
    fn with_state<T>(&self, read: impl FnOnce(&LevelState) -> T) -> T {
        match self.levels.lock() {
            Ok(state) => read(&state),
            Err(poisoned) => read(&poisoned.into_inner()),
        }
    }
}

#[pymethods]
impl PyMicrophone {
    /// Open the default input device and start capturing.
    #[new]
    fn new() -> PyResult<Self> {
        let levels = SharedLevels::default();
        let stream = device::open(&levels)?;
        #[cfg(feature = "playback")]
        let (sample_rate, channels) = (stream.sample_rate, stream.channels);
        #[cfg(not(feature = "playback"))]
        let (sample_rate, channels) = (stream.sample_rate(), stream.channels());
        Ok(Self {
            stream: Some(stream),
            levels,
            sample_rate,
            channels,
        })
    }

    /// Whether an input device exists, without opening it.
    #[staticmethod]
    fn is_available() -> bool {
        is_input_available()
    }

    /// Root-mean-square level of the most recent audio buffer, from 0.0 to 1.0.
    #[getter]
    fn level(&self) -> f32 {
        self.with_state(|state| state.current)
    }

    /// The highest level seen since opening or the last `reset_peak_level`.
    #[getter]
    fn peak_level(&self) -> f32 {
        self.with_state(|state| state.peak)
    }

    /// Forget the peak level, so `peak_level` tracks from now on.
    fn reset_peak_level(&self) {
        if let Ok(mut state) = self.levels.lock() {
            state.peak = 0.0;
        }
    }

    /// The most recent `count` levels, oldest first, one per audio buffer.
    ///
    /// At most 4096 levels are kept, which is plenty to draw a sparkline.
    fn level_history(&self, count: usize) -> PyResult<Vec<f32>> {
        if count > HISTORY_CAPACITY {
            return Err(PyValueError::new_err(format!(
                "count must be at most {HISTORY_CAPACITY}, got {count}"
            )));
        }
        Ok(self.with_state(|state| {
            let skip = state.history.len().saturating_sub(count);
            state.history.iter().skip(skip).copied().collect()
        }))
    }

    /// The most recent stream error reported by the device, if any.
    #[getter]
    fn last_error(&self) -> Option<String> {
        self.with_state(|state| state.last_error.clone())
    }

    #[getter]
    fn sample_rate(&self) -> u32 {
        self.sample_rate
    }

    #[getter]
    fn channels(&self) -> u16 {
        self.channels
    }

    /// Whether the stream is still capturing.
    #[getter]
    fn is_open(&self) -> bool {
        self.stream.is_some()
    }

    /// Stop capturing and release the device. Safe to call repeatedly.
    fn close(&mut self) {
        self.stream.take();
    }

    fn __enter__(slf: Py<Self>) -> Py<Self> {
        slf
    }

    #[pyo3(signature = (exception_type = None, exception_value = None, traceback = None))]
    fn __exit__(
        &mut self,
        exception_type: Option<Py<PyAny>>,
        exception_value: Option<Py<PyAny>>,
        traceback: Option<Py<PyAny>>,
    ) -> bool {
        let _ = (exception_type, exception_value, traceback);
        self.close();
        false
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyMicrophone>()
}
