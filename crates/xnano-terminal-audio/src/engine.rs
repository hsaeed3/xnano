//! Playback: a kira `AudioManager` plus one musical clock.
//!
//! Without the `playback` feature the crate is built with no audio device
//! support; the player still exists so the Python surface is identical, but
//! constructing one raises `TerminalAudioUnavailableError`.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::synth::{DEFAULT_SAMPLE_RATE, PyAudioEffect, PySound, render};

const DEFAULT_BEATS_PER_MINUTE: f64 = 120.0;

fn check_tempo(beats_per_minute: f64) -> PyResult<f64> {
    if beats_per_minute.is_finite() && beats_per_minute > 0.0 && beats_per_minute <= 600_000.0 {
        Ok(beats_per_minute)
    } else {
        Err(PyValueError::new_err(format!(
            "beats_per_minute must be greater than 0 and at most 600000, got {beats_per_minute}"
        )))
    }
}

fn check_gain(volume: f32, pan: f32) -> PyResult<(f32, f32)> {
    if !(-1.0..=1.0).contains(&pan) {
        return Err(PyValueError::new_err(format!(
            "pan must be between -1.0 (left) and 1.0 (right), got {pan}"
        )));
    }
    if !volume.is_finite() {
        return Err(PyValueError::new_err(format!(
            "volume must be a finite number between 0.0 and 1.0, got {volume}"
        )));
    }
    // Balance law: the centre keeps unity gain, panning only attenuates the
    // far channel.
    let gain = volume.clamp(0.0, 1.0);
    Ok((gain * (1.0 - pan).min(1.0), gain * (1.0 + pan).min(1.0)))
}

#[cfg(feature = "playback")]
mod device {
    use std::sync::Arc;

    use kira::clock::{ClockHandle, ClockSpeed, ClockTime};
    use kira::sound::static_sound::{StaticSoundData, StaticSoundSettings};
    use kira::{AudioManager, AudioManagerSettings, DefaultBackend, Frame, Tween};
    use pyo3::prelude::*;

    use crate::{audio_error, unavailable_error};

    pub struct Device {
        manager: AudioManager<DefaultBackend>,
        clock: ClockHandle,
        beats_per_minute: f64,
    }

    impl Device {
        pub fn open(beats_per_minute: f64) -> PyResult<Self> {
            crate::platform::silence_library_messages();
            let mut manager = AudioManager::<DefaultBackend>::new(AudioManagerSettings::default())
                .map_err(|error| {
                    unavailable_error(format!(
                        "could not open the default audio output device ({error}); \
                             check that an output device is connected, or use \
                             detect_audio_capabilities() to test for one first"
                    ))
                })?;
            let clock = manager
                .add_clock(ClockSpeed::TicksPerMinute(beats_per_minute))
                .map_err(audio_error)?;
            Ok(Self {
                manager,
                clock,
                beats_per_minute,
            })
        }

        pub fn play(
            &mut self,
            samples: &[f32],
            sample_rate: u32,
            (left, right): (f32, f32),
            at_beat: Option<u64>,
        ) -> PyResult<()> {
            let mut settings = StaticSoundSettings::default();
            if let Some(ticks) = at_beat {
                settings = settings.start_time(ClockTime {
                    clock: self.clock.id(),
                    ticks,
                    fraction: 0.0,
                });
            }
            let frames: Arc<[Frame]> = samples
                .iter()
                .map(|&sample| Frame {
                    left: sample * left,
                    right: sample * right,
                })
                .collect();
            let sound = StaticSoundData {
                sample_rate,
                frames,
                settings,
                slice: None,
            };
            self.manager.play(sound).map_err(audio_error)?;
            Ok(())
        }

        pub fn start_clock(&mut self) {
            self.clock.start();
        }

        pub fn pause_clock(&mut self) {
            self.clock.pause();
        }

        pub fn stop_clock(&mut self) {
            self.clock.stop();
        }

        pub fn set_tempo(&mut self, beats_per_minute: f64) {
            self.beats_per_minute = beats_per_minute;
            self.clock.set_speed(
                ClockSpeed::TicksPerMinute(beats_per_minute),
                Tween::default(),
            );
        }

        pub fn tempo(&self) -> f64 {
            self.beats_per_minute
        }

        pub fn beat(&self) -> f64 {
            let time = self.clock.time();
            time.ticks as f64 + time.fraction
        }

        pub fn is_clock_ticking(&self) -> bool {
            self.clock.ticking()
        }
    }

    /// Whether the default output device exists and reports a usable format.
    ///
    /// Some hosts list a default device even without hardware behind it (ALSA
    /// on a machine without a sound card), so the device's configuration is
    /// queried too.
    pub fn is_output_available() -> bool {
        use cpal::traits::{DeviceTrait, HostTrait};
        crate::platform::silence_library_messages();
        cpal::default_host()
            .default_output_device()
            .is_some_and(|device| device.default_output_config().is_ok())
    }
}

#[cfg(not(feature = "playback"))]
mod device {
    use pyo3::prelude::*;

    use crate::unavailable_error;

    pub enum Device {}

    impl Device {
        pub fn open(_beats_per_minute: f64) -> PyResult<Self> {
            Err(unavailable_error(crate::BUILT_WITHOUT_DEVICES))
        }

        pub fn play(
            &mut self,
            _samples: &[f32],
            _sample_rate: u32,
            _gains: (f32, f32),
            _at_beat: Option<u64>,
        ) -> PyResult<()> {
            match *self {}
        }

        pub fn start_clock(&mut self) {
            match *self {}
        }

        pub fn pause_clock(&mut self) {
            match *self {}
        }

        pub fn stop_clock(&mut self) {
            match *self {}
        }

        pub fn set_tempo(&mut self, _beats_per_minute: f64) {
            match *self {}
        }

        pub fn tempo(&self) -> f64 {
            match *self {}
        }

        pub fn beat(&self) -> f64 {
            match *self {}
        }

        pub fn is_clock_ticking(&self) -> bool {
            match *self {}
        }
    }

    pub fn is_output_available() -> bool {
        false
    }
}

pub use device::is_output_available;

/// Plays sounds and instruments on the default output device.
#[pyclass(
    name = "TerminalAudioPlayer",
    module = "xnano_audio._xnano_audio",
    unsendable
)]
pub struct PyAudioPlayer {
    device: Option<device::Device>,
}

impl PyAudioPlayer {
    fn open_device(&mut self) -> PyResult<&mut device::Device> {
        self.device.as_mut().ok_or_else(|| {
            crate::TerminalAudioError::new_err(
                "the player is closed; create a new TerminalAudioPlayer to play more sound",
            )
        })
    }
}

#[pymethods]
impl PyAudioPlayer {
    fn __repr__(slf: &Bound<'_, Self>) -> PyResult<String> {
        crate::reprs::described(slf.as_any(), &["tempo", "beat", "is_clock_running"])
    }

    /// Open the default output device.
    #[new]
    #[pyo3(signature = (*, beats_per_minute = DEFAULT_BEATS_PER_MINUTE))]
    fn new(beats_per_minute: f64) -> PyResult<Self> {
        let beats_per_minute = check_tempo(beats_per_minute)?;
        Ok(Self {
            device: Some(device::Device::open(beats_per_minute)?),
        })
    }

    /// Whether an output device exists, without opening it.
    #[staticmethod]
    fn is_available() -> bool {
        is_output_available()
    }

    /// Render a built-in instrument note and play it.
    #[pyo3(signature = (
        instrument,
        note = None,
        *,
        duration_milliseconds = 500,
        velocity = 0.8,
        effects = None,
        volume = 1.0,
        pan = 0.0,
        at_beat = None,
    ))]
    #[allow(clippy::too_many_arguments)]
    fn play_note(
        &mut self,
        py: Python<'_>,
        instrument: &str,
        note: Option<&Bound<'_, PyAny>>,
        duration_milliseconds: u32,
        velocity: f32,
        effects: Option<Vec<PyAudioEffect>>,
        volume: f32,
        pan: f32,
        at_beat: Option<u64>,
    ) -> PyResult<()> {
        let gains = check_gain(volume, pan)?;
        let default_note = "C4".into_pyobject(py)?.into_any();
        let kinds = crate::synth::effect_kinds(effects.unwrap_or_default())?;
        let sound = render(
            py,
            instrument,
            note.unwrap_or(&default_note),
            duration_milliseconds,
            velocity,
            kinds,
            DEFAULT_SAMPLE_RATE,
        )?;
        self.open_device()?
            .play(&sound.samples, sound.sample_rate, gains, at_beat)
    }

    /// Play an already rendered sound, optionally on a clock beat.
    #[pyo3(signature = (sound, *, volume = 1.0, pan = 0.0, at_beat = None))]
    fn play_sound(
        &mut self,
        sound: &PySound,
        volume: f32,
        pan: f32,
        at_beat: Option<u64>,
    ) -> PyResult<()> {
        let gains = check_gain(volume, pan)?;
        self.open_device()?
            .play(&sound.samples, sound.sample_rate, gains, at_beat)
    }

    /// Start the clock.
    fn start_clock(&mut self) -> PyResult<()> {
        self.open_device()?.start_clock();
        Ok(())
    }

    /// Pause the clock, keeping its position.
    fn pause_clock(&mut self) -> PyResult<()> {
        self.open_device()?.pause_clock();
        Ok(())
    }

    /// Stop the clock and reset it to beat zero.
    fn stop_clock(&mut self) -> PyResult<()> {
        self.open_device()?.stop_clock();
        Ok(())
    }

    /// Whether the clock is currently running.
    #[getter]
    fn is_clock_running(&self) -> bool {
        self.device
            .as_ref()
            .is_some_and(device::Device::is_clock_ticking)
    }

    /// The clock tempo in beats per minute.
    #[getter]
    fn tempo(&self) -> f64 {
        self.device.as_ref().map_or(0.0, device::Device::tempo)
    }

    /// Change the clock tempo.
    fn set_tempo(&mut self, beats_per_minute: f64) -> PyResult<()> {
        let beats_per_minute = check_tempo(beats_per_minute)?;
        self.open_device()?.set_tempo(beats_per_minute);
        Ok(())
    }

    /// The clock position in beats, including the fraction of the current beat.
    #[getter]
    fn beat(&self) -> f64 {
        self.device.as_ref().map_or(0.0, device::Device::beat)
    }

    /// The clock position in milliseconds at the current tempo.
    #[getter]
    fn clock_position_milliseconds(&self) -> f64 {
        self.device
            .as_ref()
            .map_or(0.0, |device| device.beat() * 60_000.0 / device.tempo())
    }

    /// Close owned audio output; repeated calls are safe.
    fn close(&mut self) {
        self.device = None;
    }

    fn __enter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    #[pyo3(signature = (exception_type = None, exception_value = None, traceback = None))]
    fn __exit__(
        &mut self,
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
    m.add_class::<PyAudioPlayer>()
}
