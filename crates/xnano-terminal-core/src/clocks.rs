//! `Clock` and `SimulationClock`.

use std::sync::Arc;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use xnano_terminal_runtime::clock::{Clock, SimulationClock};

#[pyclass(name = "Clock", module = "xnano_core._xnano_core", frozen)]
pub struct PyClock {
    pub inner: Arc<Clock>,
}

#[pymethods]
impl PyClock {
    #[classmethod]
    #[pyo3(signature = (*, elapsed_seconds = 0.0, frame = 0))]
    fn monotonic(
        _cls: &Bound<'_, pyo3::types::PyType>,
        elapsed_seconds: f64,
        frame: i64,
    ) -> PyResult<Self> {
        check_elapsed(elapsed_seconds)?;
        if frame < 0 {
            return Err(PyValueError::new_err(format!(
                "Clock.monotonic needs a frame of zero or more, but frame is {frame}. Pass the \
                 number of frames the clock has already counted."
            )));
        }
        Ok(Self {
            inner: Clock::monotonic_from(elapsed_seconds, frame as u64),
        })
    }

    #[classmethod]
    #[pyo3(signature = (*, elapsed_seconds = 0.0))]
    fn manual(_cls: &Bound<'_, pyo3::types::PyType>, elapsed_seconds: f64) -> PyResult<Self> {
        check_elapsed(elapsed_seconds)?;
        Ok(Self {
            inner: Clock::manual(elapsed_seconds),
        })
    }

    #[getter]
    fn source(&self) -> &'static str {
        self.inner.source().name()
    }

    #[getter]
    fn elapsed_seconds(&self) -> f64 {
        self.inner.elapsed_seconds()
    }

    #[getter]
    fn elapsed_milliseconds(&self) -> f64 {
        self.inner.elapsed_seconds() * 1000.0
    }

    #[getter]
    fn delta_seconds(&self) -> f64 {
        self.inner.delta_seconds()
    }

    #[getter]
    fn delta_milliseconds(&self) -> f64 {
        self.inner.delta_seconds() * 1000.0
    }

    #[getter]
    fn frame(&self) -> u64 {
        self.inner.frame()
    }

    #[getter]
    fn frames_per_second(&self) -> f64 {
        self.inner.frames_per_second()
    }

    #[getter]
    fn is_stopped(&self) -> bool {
        self.inner.is_paused()
    }

    fn stop(&self) {
        self.inner.pause();
    }

    fn resume(&self) {
        self.inner.resume();
    }

    fn advance(&self, milliseconds: i64) -> PyResult<()> {
        if milliseconds < 0 {
            return Err(PyValueError::new_err(format!(
                "Clock.advance cannot move time backwards: {milliseconds} milliseconds is negative. \
                 Pass zero or more milliseconds."
            )));
        }
        if !self.inner.advance(milliseconds as u64) {
            return Err(PyValueError::new_err(
                "only a manual clock can be advanced; create one with Clock.manual() for \
                 deterministic tests",
            ));
        }
        Ok(())
    }

    fn step(&self, milliseconds: i64) -> PyResult<()> {
        if milliseconds < 0 {
            return Err(PyValueError::new_err(format!(
                "Clock.step cannot move time backwards: {milliseconds} milliseconds is negative. \
                 Pass zero or more milliseconds."
            )));
        }
        if !self.inner.step(milliseconds as u64) {
            return Err(PyValueError::new_err(
                "A running wall clock cannot be stepped by hand. Call stop() first, or use a \
                 manual clock.",
            ));
        }
        Ok(())
    }

    #[pyo3(signature = (*, rate = 1.0, is_stopped = false))]
    fn derive(&self, rate: f64, is_stopped: bool) -> PyResult<PySimulationClock> {
        check_rate(rate)?;
        Ok(PySimulationClock {
            inner: self.inner.derive(rate, is_stopped),
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "Clock(source='{}', elapsed_seconds={:.3})",
            self.source(),
            self.elapsed_seconds()
        )
    }
}

fn check_elapsed(elapsed_seconds: f64) -> PyResult<()> {
    if !elapsed_seconds.is_finite() || elapsed_seconds < 0.0 {
        return Err(PyValueError::new_err(
            "elapsed_seconds must be a finite number that is zero or more",
        ));
    }
    Ok(())
}

fn check_rate(rate: f64) -> PyResult<()> {
    if !rate.is_finite() || rate < 0.0 {
        return Err(PyValueError::new_err(format!(
            "a simulation rate must be a finite number that is zero or more, not {rate}"
        )));
    }
    Ok(())
}

#[pyclass(name = "SimulationClock", module = "xnano_core._xnano_core", frozen)]
pub struct PySimulationClock {
    pub inner: Arc<SimulationClock>,
}

#[pymethods]
impl PySimulationClock {
    #[getter]
    fn parent(&self) -> PyClock {
        PyClock {
            inner: Arc::clone(self.inner.parent()),
        }
    }

    #[getter]
    fn rate(&self) -> f64 {
        self.inner.rate()
    }

    #[setter]
    fn set_rate(&self, value: f64) -> PyResult<()> {
        check_rate(value)?;
        self.inner.set_rate(value);
        Ok(())
    }

    #[getter]
    fn is_stopped(&self) -> bool {
        self.inner.is_paused()
    }

    #[setter]
    fn set_is_stopped(&self, value: bool) {
        self.inner.set_paused(value);
    }

    #[getter]
    fn elapsed_seconds(&self) -> f64 {
        self.inner.elapsed_seconds()
    }

    #[getter]
    fn delta_seconds(&self) -> f64 {
        self.inner.delta_seconds()
    }

    fn sample(&self) {
        self.inner.sample();
    }

    fn stop(&self) {
        self.inner.set_paused(true);
    }

    fn resume(&self) {
        self.inner.set_paused(false);
    }

    fn __repr__(&self) -> String {
        format!(
            "SimulationClock(rate={}, is_stopped={}, elapsed_seconds={:.3})",
            self.inner.rate(),
            if self.inner.is_paused() {
                "True"
            } else {
                "False"
            },
            self.inner.elapsed_seconds()
        )
    }
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyClock>()?;
    m.add_class::<PySimulationClock>()
}
