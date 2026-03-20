use crate::{optimizer, reliability, simulate};
use std::ffi::{CStr, CString};
use std::os::raw::c_char;

fn c_string_from_json_or_error(result: Result<String, String>) -> *mut c_char {
    let payload = match result {
        Ok(json) => json,
        Err(err) => serde_json::json!({ "error": err }).to_string(),
    };

    match CString::new(payload) {
        Ok(cstr) => cstr.into_raw(),
        Err(_) => CString::new("{\"error\":\"CString conversion failed\"}")
            .expect("literal JSON must be CString-safe")
            .into_raw(),
    }
}

fn read_cstr(ptr: *const c_char) -> Result<String, String> {
    if ptr.is_null() {
        return Err("null pointer request".to_string());
    }

    // Safety: caller guarantees a valid, NUL-terminated string pointer.
    let cstr = unsafe { CStr::from_ptr(ptr) };
    cstr.to_str()
        .map_err(|_| "request is not valid UTF-8".to_string())
        .map(|text| text.to_string())
}

#[no_mangle]
pub extern "C" fn sram_simulate_from_json(req_json: *const c_char) -> *mut c_char {
    let result = (|| {
        let req_text = read_cstr(req_json)?;
        let req: simulate::SimulateRequest =
            serde_json::from_str(&req_text).map_err(|err| format!("invalid request: {err}"))?;
        let resp = simulate::simulate_array(&req)?;
        serde_json::to_string(&resp).map_err(|err| format!("serialization failed: {err}"))
    })();
    c_string_from_json_or_error(result)
}

#[no_mangle]
pub extern "C" fn sram_predict_lifetime_from_json(req_json: *const c_char) -> *mut c_char {
    let result = (|| {
        let req_text = read_cstr(req_json)?;
        let req: reliability::LifetimeRequest =
            serde_json::from_str(&req_text).map_err(|err| format!("invalid request: {err}"))?;
        let resp = reliability::predict_lifetime(&req)?;
        serde_json::to_string(&resp).map_err(|err| format!("serialization failed: {err}"))
    })();
    c_string_from_json_or_error(result)
}

#[no_mangle]
pub extern "C" fn sram_optimize_design_from_json(req_json: *const c_char) -> *mut c_char {
    let result = (|| {
        let req_text = read_cstr(req_json)?;
        let req: optimizer::OptimizeRequest =
            serde_json::from_str(&req_text).map_err(|err| format!("invalid request: {err}"))?;
        let resp = optimizer::optimize_design(&req)?;
        serde_json::to_string(&resp).map_err(|err| format!("serialization failed: {err}"))
    })();
    c_string_from_json_or_error(result)
}

#[no_mangle]
pub extern "C" fn sram_free_string(ptr: *mut c_char) {
    if ptr.is_null() {
        return;
    }

    // Safety: pointer must be allocated by CString::into_raw in this library.
    unsafe {
        let _ = CString::from_raw(ptr);
    }
}
