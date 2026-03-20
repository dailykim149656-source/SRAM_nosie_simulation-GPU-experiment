cmake_minimum_required(VERSION 3.20)
project(eda_bridge LANGUAGES CXX)

add_library(eda_bridge STATIC
    src/eda_bridge.cpp
)

target_include_directories(eda_bridge
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_features(eda_bridge PUBLIC cxx_std_17)

# Optional: pass a prebuilt Rust core library path at configure time.
# Example:
#   cmake -DSRAM_RUST_CORE_LIB=/path/to/libsram_native_core.a ...
set(SRAM_RUST_CORE_LIB "" CACHE STRING "Path to Rust core static or shared library")
if(SRAM_RUST_CORE_LIB)
    target_link_libraries(eda_bridge PRIVATE ${SRAM_RUST_CORE_LIB})
endif()

