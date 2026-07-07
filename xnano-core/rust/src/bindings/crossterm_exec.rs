use std::io::{stdout, Write};

use crossterm::ExecutableCommand;
use pyo3::prelude::*;

pub fn io_to_py(err: std::io::Error) -> PyErr {
    pyo3::exceptions::PyIOError::new_err(err.to_string())
}

pub fn execute_stdout(command: impl crossterm::Command) -> PyResult<()> {
    stdout()
        .execute(command)
        .map_err(io_to_py)?;
    Ok(())
}

pub fn flush_stdout() -> PyResult<()> {
    stdout().flush().map_err(io_to_py)?;
    Ok(())
}
