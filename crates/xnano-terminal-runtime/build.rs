//! Keeps the root `pyproject.toml` (the `xnano` metapackage) in step with the Cargo workspace.
//!
//! The workspace version is the single source of truth for the `xnano` and `xnano-core`
//! versions; each other binding crate's own version sets its distribution pin. Like pydantic's `monty`,
//! the metapackage has no Cargo package of its own, so the build script of the always-built
//! engine crate maintains it. `xnano-core` is the metapackage's only dependency; `xnano-audio`
//! and `xnano-image` are its `audio` and `image` extras. A source distribution legitimately has no metapackage and is left
//! alone.

use std::{
    env,
    fmt::Write as _,
    fs,
    path::{Path, PathBuf},
};

/// The distributions the metapackage pins, with the directory holding each crate.
const PINNED_DISTRIBUTIONS: [(&str, &str); 3] = [
    ("xnano-core", "crates/xnano-terminal-core"),
    ("xnano-audio", "crates/xnano-terminal-audio"),
    ("xnano-image", "crates/xnano-terminal-image"),
];

fn main() {
    let root = PathBuf::from(env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR is set"))
        .join("../..");
    let pyproject = root.join("pyproject.toml");
    if !pyproject.is_file() {
        println!(
            "cargo:warning=no file at {}, skipping version sync",
            pyproject.display()
        );
        return;
    }
    println!("cargo:rerun-if-changed={}", pyproject.display());
    println!("cargo:rerun-if-changed=../../Cargo.toml");
    let version = env::var("CARGO_PKG_VERSION").expect("CARGO_PKG_VERSION is set");
    let mut pins = Vec::new();
    for (distribution, directory) in PINNED_DISTRIBUTIONS {
        let manifest = root.join(directory).join("Cargo.toml");
        println!("cargo:rerun-if-changed={}", manifest.display());
        let Some(crate_version) = read_version(&manifest) else {
            println!(
                "cargo:warning=could not read the version in {}, skipping pin sync",
                manifest.display()
            );
            return;
        };
        assert!(
            distribution != "xnano-core" || crate_version == version,
            "xnano and xnano-core must share a version: workspace is {version}, \
             but {} declares {crate_version}",
            manifest.display()
        );
        pins.push((
            distribution,
            format!("    \"{distribution}{}\",", pin_specifier(&crate_version)),
        ));
    }
    sync(&pyproject, &pep440(&version), &pins);
}

/// `version = "..."` of the `[package]` table.
fn read_version(manifest: &Path) -> Option<String> {
    let contents = fs::read_to_string(manifest).ok()?;
    let mut in_package = false;
    for line in contents.lines() {
        let line = line.trim();
        if line.starts_with('[') {
            in_package = line == "[package]";
        } else if in_package && let Some(rest) = line.strip_prefix("version = \"") {
            return rest.strip_suffix('"').map(str::to_owned);
        }
    }
    None
}

/// A Cargo version such as `1.0.0-beta.1` as the PEP 440 version `1.0.0b1`.
fn pep440(version: &str) -> String {
    let Some((release, pre)) = version.split_once('-') else {
        return version.to_owned();
    };
    let (label, number) = pre.split_once('.').unwrap_or((pre, "0"));
    let tag = match label {
        "alpha" => "a",
        "beta" => "b",
        "rc" => "rc",
        other => return format!("{release}.{other}{number}"),
    };
    format!("{release}{tag}{number}")
}

/// `>=1.0.0b1` for stable-major crates; `>=0.1.0,<0.2` for crates below 1.0, whose minor
/// version is the breaking one.
fn pin_specifier(version: &str) -> String {
    let python = pep440(version);
    let release = version.split('-').next().unwrap_or(version);
    let mut parts = release.split('.');
    let major: u64 = parts.next().and_then(|part| part.parse().ok()).unwrap_or(0);
    let minor: u64 = parts.next().and_then(|part| part.parse().ok()).unwrap_or(0);
    if major == 0 {
        format!(">={python},<0.{}", minor + 1)
    } else {
        format!(">={python}")
    }
}

fn sync(pyproject: &Path, version: &str, pins: &[(&str, String)]) {
    let contents = fs::read_to_string(pyproject).expect("pyproject.toml is readable");
    let mut output = String::with_capacity(contents.len());
    let mut region = false;
    let mut in_dependencies = false;
    let mut wrote_pins = false;
    let mut is_replacing_extras = false;
    for line in contents.lines() {
        if line.contains("[! AUTO-VERSIONING") {
            region = true;
            output.push_str(line);
            output.push('\n');
            continue;
        }
        if line.contains("[! END AUTO-VERSIONING]") {
            region = false;
            is_replacing_extras = false;
        }
        if region {
            if line.starts_with("version = ") {
                let _ = writeln!(output, "version = '{version}'");
                continue;
            }
            if line.starts_with("dependencies = [") {
                in_dependencies = true;
                output.push_str("dependencies = [\n");
                for (distribution, pin) in pins {
                    if *distribution == "xnano-core" {
                        output.push_str(pin);
                        output.push('\n');
                    }
                }
                wrote_pins = true;
                continue;
            }
            if in_dependencies {
                if line.trim() == "]" {
                    in_dependencies = false;
                    output.push_str("]\n\n[project.optional-dependencies]\n");
                    for (distribution, pin) in pins {
                        if let Some(extra) = distribution.strip_prefix("xnano-")
                            && *distribution != "xnano-core"
                        {
                            let _ = writeln!(output, "{extra} = [\n{pin}\n]");
                        }
                    }
                    is_replacing_extras = true;
                }
                continue;
            }
            if is_replacing_extras {
                continue;
            }
        }
        output.push_str(line);
        output.push('\n');
    }
    assert!(
        wrote_pins,
        "pyproject.toml needs a `dependencies = [` list between the AUTO-VERSIONING markers"
    );
    if output != contents {
        eprintln!("Updating {} to {version}", pyproject.display());
        fs::write(pyproject, output).expect("pyproject.toml is writable");
    }
}
