//! `xnano-audio`: native audio engine for xnano.
//!
//! Deliberately decoupled from `xnano-core`: this crate owns the platform audio
//! libraries (and, on Linux, the system ALSA dependency), so that failing to
//! load it can never affect the terminal core. Device support lives behind the
//! `playback` feature; without it, synthesis still works and the device classes
//! report that they are unavailable.

mod dsp;
mod effects;
mod engine;
mod instruments;
mod melody;
mod melody_python;
mod microphone;
mod pcm;
mod pitch;
#[cfg(feature = "playback")]
#[allow(unsafe_code)]
mod platform;
mod streaming;
mod synth;

use pyo3::create_exception;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;

create_exception!(
    xnano_audio._xnano_audio,
    TerminalAudioError,
    PyRuntimeError,
    "Raised when an audio device or stream fails."
);

create_exception!(
    xnano_audio._xnano_audio,
    TerminalAudioUnavailableError,
    TerminalAudioError,
    "Raised when audio devices are missing or this build has no device support."
);

pub(crate) const BUILT_WITHOUT_DEVICES: &str = "this build of xnano-audio has no audio \
    device support because it was built without the `playback` feature; synthesis with \
    render_note and TerminalSound still works. Install a prebuilt wheel with device support, \
    or build for a supported native platform with the `playback` feature enabled";

/// Convert any displayable audio-library error into a `TerminalAudioError`.
#[cfg_attr(not(feature = "playback"), allow(dead_code))]
pub(crate) fn audio_error(error: impl std::fmt::Display) -> PyErr {
    TerminalAudioError::new_err(format!("audio device error: {error}"))
}

/// Build a `TerminalAudioUnavailableError` with a message that explains recovery.
pub(crate) fn unavailable_error(message: impl Into<String>) -> PyErr {
    TerminalAudioUnavailableError::new_err(message.into())
}

/// What audio support this build and machine offer.
#[pyclass(
    name = "TerminalAudioCapabilities",
    module = "xnano_audio._xnano_audio",
    frozen,
    eq,
    from_py_object
)]
#[derive(Clone, PartialEq, Eq)]
struct PyAudioCapabilities {
    /// Whether this build was compiled with audio device support.
    #[pyo3(get)]
    has_device_support: bool,
    /// Whether a default output device exists.
    #[pyo3(get)]
    is_output_available: bool,
    /// Whether a default input device (microphone) exists.
    #[pyo3(get)]
    is_input_available: bool,
}

#[pymethods]
impl PyAudioCapabilities {
    fn __repr__(&self) -> String {
        let name = |value: bool| if value { "True" } else { "False" };
        format!(
            "TerminalAudioCapabilities(has_device_support={}, is_output_available={}, \
             is_input_available={})",
            name(self.has_device_support),
            name(self.is_output_available),
            name(self.is_input_available),
        )
    }

    /// Why output is unavailable, or ``None`` when it is available.
    #[getter]
    fn output_unavailable_reason(&self) -> Option<&'static str> {
        if !self.has_device_support {
            Some(BUILT_WITHOUT_DEVICES)
        } else if !self.is_output_available {
            Some("no default audio output device was found")
        } else {
            None
        }
    }

    /// Why input is unavailable, or ``None`` when it is available.
    #[getter]
    fn input_unavailable_reason(&self) -> Option<&'static str> {
        if !self.has_device_support {
            Some(BUILT_WITHOUT_DEVICES)
        } else if !self.is_input_available {
            Some("no default audio input device (microphone) was found")
        } else {
            None
        }
    }
}

/// Report what audio support is available, without opening any device.
#[pyfunction]
fn detect_audio_capabilities(py: Python<'_>) -> PyAudioCapabilities {
    py.detach(|| PyAudioCapabilities {
        has_device_support: cfg!(feature = "playback"),
        is_output_available: engine::is_output_available(),
        is_input_available: microphone::is_input_available(),
    })
}

#[pymodule(gil_used = false)]
fn _xnano_audio(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add(
        "is_optimized_build",
        option_env!("XNANO_OPTIMIZATION_LEVEL") != Some("0"),
    )?;
    m.add(
        "TerminalAudioError",
        m.py().get_type::<TerminalAudioError>(),
    )?;
    m.add(
        "TerminalAudioUnavailableError",
        m.py().get_type::<TerminalAudioUnavailableError>(),
    )?;
    m.add_class::<PyAudioCapabilities>()?;
    m.add_function(wrap_pyfunction!(detect_audio_capabilities, m)?)?;
    engine::register(m)?;
    microphone::register(m)?;
    synth::register(m)?;
    melody_python::register(m)?;
    pcm::register(m)?;
    streaming::register(m)?;
    Ok(())
}
