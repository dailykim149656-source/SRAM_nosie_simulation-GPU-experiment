use pyo3::prelude::*;

mod optimizer;
mod reliability;
mod simulate;
pub mod c_api;

#[pyfunction]
fn simulate_array(req_json: &str) -> PyResult<String> {
    let request: simulate::SimulateRequest = serde_json::from_str(req_json).map_err(|err| {
        pyo3::exceptions::PyValueError::new_err(format!("invalid simulate request: {err}"))
    })?;

    let response = simulate::simulate_array(&request).map_err(|err| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("simulate failed: {err}"))
    })?;

    serde_json::to_string(&response).map_err(|err| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("simulate serialization failed: {err}"))
    })
}

#[pyfunction]
fn predict_lifetime(req_json: &str) -> PyResult<String> {
    let request: reliability::LifetimeRequest =
        serde_json::from_str(req_json).map_err(|err| {
            pyo3::exceptions::PyValueError::new_err(format!("invalid lifetime request: {err}"))
        })?;

    let response = reliability::predict_lifetime(&request).map_err(|err| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("predict_lifetime failed: {err}"))
    })?;

    serde_json::to_string(&response).map_err(|err| {
        pyo3::exceptions::PyRuntimeError::new_err(format!(
            "predict_lifetime serialization failed: {err}"
        ))
    })
}

#[pyfunction]
fn optimize_design(req_json: &str) -> PyResult<String> {
    let request: optimizer::OptimizeRequest = serde_json::from_str(req_json).map_err(|err| {
        pyo3::exceptions::PyValueError::new_err(format!("invalid optimize request: {err}"))
    })?;

    let response = optimizer::optimize_design(&request).map_err(|err| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("optimize_design failed: {err}"))
    })?;

    serde_json::to_string(&response).map_err(|err| {
        pyo3::exceptions::PyRuntimeError::new_err(format!(
            "optimize_design serialization failed: {err}"
        ))
    })
}

#[pymodule]
fn _sram_native(_py: Python<'_>, module: &PyModule) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(simulate_array, module)?)?;
    module.add_function(wrap_pyfunction!(predict_lifetime, module)?)?;
    module.add_function(wrap_pyfunction!(optimize_design, module)?)?;
    Ok(())
}

