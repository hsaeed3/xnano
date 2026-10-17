fn main() {
    pyo3_build_config::use_pyo3_cfgs();
    // Whether the code is optimized depends on the optimization level, not on assertions.
    // A build instrumented for coverage runs several times slower than a release build, so
    // it counts as not optimized and the speed budgets skip it.
    let is_instrumented = std::env::var("CARGO_ENCODED_RUSTFLAGS")
        .is_ok_and(|flags| flags.contains("instrument-coverage"));
    let level = if is_instrumented {
        "0".to_owned()
    } else {
        std::env::var("OPT_LEVEL").unwrap_or_else(|_| "0".to_owned())
    };
    println!("cargo:rustc-env=XNANO_OPTIMIZATION_LEVEL={level}");
    println!("cargo:rerun-if-env-changed=CARGO_ENCODED_RUSTFLAGS");
}
