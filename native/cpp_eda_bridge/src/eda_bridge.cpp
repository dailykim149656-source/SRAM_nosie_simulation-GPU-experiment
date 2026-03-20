#include "eda_bridge.hpp"

#include <stdexcept>
#include <string>

extern "C" {
char* sram_simulate_from_json(const char* req_json);
char* sram_predict_lifetime_from_json(const char* req_json);
char* sram_optimize_design_from_json(const char* req_json);
void sram_free_string(char* ptr);
}

namespace sram::eda {
namespace {

using RustJsonFn = char* (*)(const char*);

std::string call_rust_json(RustJsonFn fn, const std::string& request_json) {
    if (fn == nullptr) {
        throw std::runtime_error("Rust function pointer is null");
    }

    char* raw = fn(request_json.c_str());
    if (raw == nullptr) {
        throw std::runtime_error("Rust function returned null");
    }

    std::string response(raw);
    sram_free_string(raw);
    return response;
}

}  // namespace

std::string EdaBridge::simulateSramJson(const std::string& request_json) const {
    return call_rust_json(sram_simulate_from_json, request_json);
}

std::string EdaBridge::predictLifetimeJson(const std::string& request_json) const {
    return call_rust_json(sram_predict_lifetime_from_json, request_json);
}

std::string EdaBridge::optimizeDesignJson(const std::string& request_json) const {
    return call_rust_json(sram_optimize_design_from_json, request_json);
}

}  // namespace sram::eda

