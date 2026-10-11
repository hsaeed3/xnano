.DEFAULT_GOAL := help
# Python packages live in `packages/`, and every Rust crate lives in `crates/` (one Cargo workspace).
packages = xnano-core xnano-audio xnano-image
sources = packages scripts .github/scripts
NUM_THREADS?=1

# This is used to stop uv from rebuilding a .so file through `uv run` invoked operations
uv-run-no-sync = uv run --no-sync

# `xnano-audio` links the system ALSA library on Linux. When its development
# headers are missing, the package is built without audio device support instead
# of failing the whole install (synthesis still works; devices report unavailable).
audio-sync-settings := $(shell if [ "$$(uname -s)" = "Linux" ] && ! pkg-config --exists alsa 2>/dev/null; then echo "--config-settings-package xnano-audio:maturin.build-args=--no-default-features"; fi)
uv-sync = uv sync --frozen --all-groups --all-packages --all-extras $(audio-sync-settings)

.PHONY: .audio-notice
.audio-notice:
	@if [ -n "$(audio-sync-settings)" ]; then echo "ALSA development headers were not found: building xnano-audio without audio device support. Install libasound2-dev (Debian/Ubuntu) or alsa-lib-devel (Fedora) and rerun to enable playback and microphone input."; fi

.PHONY: check  ## Run the standard set of checks performed in CI
check: lint-all spellcheck typecheck test-coverage

.PHONY: .uv ## Ensures that uv is installed and available in the PATH.
.uv:
	@uv -V > /dev/null 2>&1 || (echo "uv is not installed. Please install it from https://docs.astral.sh/uv/getting-started/installation/"; exit 1)
	@echo "uv is installed and available in the PATH."

.PHONY: .prek ## Ensures prek (pre-commit) is installed in the uv workspace
.prek: .uv
	@uv run --no-sync prek -V > /dev/null 2>&1 || (echo "prek is not installed. Run `make install` to sync the development tools."; exit 1)
	@echo "prek is installed and available in the PATH."

.PHONY: .rust  # Check that Rust is installed
.rust:
	@rustup --version > /dev/null 2>&1 || (echo "Rust is not installed. Please install it from https://rust-lang.org/tools/install/"; exit 1)
	@echo "Rust is installed and available in the PATH."

.PHONY: install  ## Install every package & local development groups
install: .uv .rust .audio-notice
	@set -e; for package in $(packages); do $(MAKE) -C packages/$$package clean; done
	$(MAKE) rebuild-rust
	$(uv-sync)
	uv run prek install --install-hooks

.PHONY: rebuild-rust ## Rebuilds the Rust extensions of all packages
rebuild-rust: .uv .rust
	@set -e; for package in $(packages); do $(MAKE) -C packages/$$package rebuild-rust; done

.PHONY: rebuild ## Rebuilds all rust extensions & syncs xnano's root uv workspace
rebuild: .uv .rust .audio-notice
	$(MAKE) rebuild-rust
	$(uv-sync)

.PHONY: rebuild-lockfiles  ## Rebuild lockfiles from scratch, updating all dependencies
rebuild-lockfiles: .uv
	uv lock --upgrade

.PHONY: format  ## Auto-format the python source files of every package
format: .uv
	$(uv-run-no-sync) ruff check --fix $(sources)
	$(uv-run-no-sync) ruff format $(sources)

.PHONY: format-all  ## Auto-format all python & rust source files
format-all: .uv
	$(MAKE) format
	cargo fmt --all

.PHONY: lint ## Lints the python source files of every package
lint: .uv
	$(uv-run-no-sync) ruff check $(sources)
	$(uv-run-no-sync) ruff format --check $(sources)
	$(uv-run-no-sync) griffe dump -f -d google -LWARNING -o/dev/null xnano -s packages/xnano-core/src
	$(uv-run-no-sync) griffe dump -f -d google -LWARNING -o/dev/null xnano_audio -s packages/xnano-audio/src
	$(uv-run-no-sync) griffe dump -f -d google -LWARNING -o/dev/null xnano_image -s packages/xnano-image/src

.PHONY: lint-rust  ## Lints every Rust crate of the workspace
lint-rust:
	cargo fmt --version
	cargo fmt --all -- --check
	cargo clippy --version
	cargo clippy --workspace --all-targets -- -D warnings

.PHONY: lint-all  ## Lints all python & rust source files
lint-all: lint lint-rust

.PHONY: spellcheck  ## Runs spellcheck with codespell
spellcheck: .uv
	$(uv-run-no-sync) prek run codespell --all-files

.PHONY: typecheck ## Perform type-checking
typecheck: .uv
	$(uv-run-no-sync) basedpyright

.PHONY: test-rust  ## Run the pure Rust test suites
test-rust: .rust
	cargo test -p xnano-terminal-cells -p xnano-terminal-state -p xnano-terminal-runtime
	cargo test -p xnano-terminal-audio --lib

.PHONY: test-coverage ## Run tests and generate a coverage report
test-coverage: .uv
	@set -e; for package in $(packages); do $(MAKE) -C packages/$$package test-coverage; done

.PHONY: benchmark-all ## Run every package's benchmarks against optimized builds
benchmark-all: .uv
	@set -e; for package in $(packages); do $(MAKE) -C packages/$$package benchmark; done

.PHONY: test  ## Run all tests without building the packages
test: test-rust
	@set -e; for package in $(packages); do $(MAKE) -C packages/$$package test; done

.PHONY: test-sync ## Runs all tests after syncing every package with uv
test-sync: .uv
	$(uv-sync)
	@set -e; for package in $(packages); do $(MAKE) -C packages/$$package test; done

.PHONY: clean  ## Clear local caches and build artifacts
clean:
	cargo clean
	rm -rf `find . -name target -not -path './.venv/*'`
	rm -rf `find . -name __pycache__ -not -path './.venv/*'`
	rm -f `find . -type f -name '*.py[co]' -not -path './.venv/*'`
	rm -f `find . -type f -name '*~' -not -path './.venv/*'`
	rm -f `find . -type f -name '.*~' -not -path './.venv/*'`
	find packages -name '*.so' -delete
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf .ruff_cache
		rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -f coverage.lcov
	rm -rf build
	rm -rf dist
	rm -rf site

.PHONY: docs-build  ## Build static site for documentation
docs-build: .uv
	uv run --only-group docs zensical build --clean --strict --config-file ./zensical.toml

.PHONY: version-check  ## Check Cargo and generated Python/documentation versions are synchronized
version-check:
	$(uv-run-no-sync) python scripts/set_version.py --check

.PHONY: set-version  ## Bump a package: make set-version PACKAGE=xnano-core VERSION=1.2.3
set-version:
	@test -n "$(PACKAGE)" -a -n "$(VERSION)" || (echo "Usage: make set-version PACKAGE=xnano-core VERSION=1.2.3"; exit 2)
	$(uv-run-no-sync) python scripts/set_version.py "$(PACKAGE)" "$(VERSION)"

.PHONY: docs-serve  ## Build and serve the documentation, for local preview
docs-serve: .uv
	uv run --only-group docs zensical serve --config-file ./zensical.toml

.PHONY: help  ## Display this message
help:
	@grep -E \
		'^.PHONY: .*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ".PHONY: |## "}; {printf "\033[36m%-19s\033[0m %s\n", $$2, $$3}'
