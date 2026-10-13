fn main() {
    pyo3_build_config::use_pyo3_cfgs();
    // Whether the code is optimized depends on the optimization level, not on assertions.
    println!(
        "cargo:rustc-env=XNANO_OPTIMIZATION_LEVEL={}",
        std::env::var("OPT_LEVEL").unwrap_or_else(|_| "0".to_owned())
    );
}
