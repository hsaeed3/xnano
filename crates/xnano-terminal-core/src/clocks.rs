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
    fn monotonic(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self {
            inner: Clock::monotonic(),
        }
    }

    #[classmethod]
    #[pyo3(signature = (*, elapsed_seconds = 0.0))]
    fn manual(_cls: &Bound<'_, pyo3::types::PyType>, elapsed_seconds: f64) -> PyResult<Self> {
        if !elapsed_seconds.is_finite() || elapsed_seconds < 0.0 {
            return Err(PyValueError::new_err(
                "elapsed_seconds must be a finite number that is zero or more",
            ));
        }
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
    fn is_paused(&self) -> bool {
        self.inner.is_paused()
    }

    fn pause(&self) {
        self.inner.pause();
    }

    fn resume(&self) {
        self.inner.resume();
    }

    fn advance(&self, milliseconds: i64) -> PyResult<()> {
        if milliseconds < 0 {
            return Err(PyValueError::new_err(format!(
                "a clock cannot move backwards: advance by {milliseconds} milliseconds is negative; \
                 pass zero or more"
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

    #[pyo3(signature = (*, rate = 1.0, paused = false))]
    fn derive(&self, rate: f64, paused: bool) -> PyResult<PySimulationClock> {
        check_rate(rate)?;
        Ok(PySimulationClock {
            inner: self.inner.derive(rate, paused),
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
    fn paused(&self) -> bool {
        self.inner.is_paused()
    }

    #[setter]
    fn set_paused(&self, value: bool) {
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

    fn pause(&self) {
        self.inner.set_paused(true);
    }

    fn resume(&self) {
        self.inner.set_paused(false);
    }

    fn __repr__(&self) -> String {
        format!(
            "SimulationClock(rate={}, paused={}, elapsed_seconds={:.3})",
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
