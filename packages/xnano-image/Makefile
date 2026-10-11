.DEFAULT_GOAL := help
# The Rust crate of this package lives in the workspace root (`../../crates/<crate>`).
crate = xnano-terminal-image
module = xnano_image
sources = src tests

# This is used to stop uv from rebuilding a .so file through `uv run` invoked operations
uv-run-no-sync = uv run --no-sync

.PHONY: check  ## Run the standard set of checks performed in CI
check: lint test-coverage

.PHONY: .uv ## Ensures that uv is installed and available in the PATH.
.uv:
	@uv -V > /dev/null 2>&1 || (echo "uv is not installed. Please install it from https://docs.astral.sh/uv/getting-started/installation/"; exit 1)
	@echo "uv is installed and available in the PATH."

.PHONY: install  ## Install the package, dependencies, and pre-commit for local development
install: .uv
	uv sync --frozen --all-groups
	uv run prek install --install-hooks

.PHONY: rebuild-rust  ## Rebuilds the .so file for the rust extension
rebuild-rust: .uv
	cargo clean -p $(crate)
	uv run maturin develop --uv

.PHONY: build-dev  ## Build the development version of the package
build-dev: .uv
	@find src -name '*.so' -delete
	$(uv-run-no-sync) maturin develop --uv

.PHONY: build-profiling  ## Build the profiling version of the package
build-profiling: .uv
	@find src -name '*.so' -delete
	$(uv-run-no-sync) maturin develop --uv --profile profiling

.PHONY: build-coverage  ## Build the coverage version of the package
build-coverage: .uv
	@find src -name '*.so' -delete
	RUSTFLAGS='-C instrument-coverage' $(uv-run-no-sync) maturin develop --uv --release

.PHONY: build-pgo  ## Build the PGO version of the package
build-pgo: .uv
	@find src -name '*.so' -delete
	$(uv-run-no-sync) maturin develop --uv --pgo

.PHONY: build-wasm  ## Build the WebAssembly version of the package
build-wasm: .uv
	@echo 'This requires python 3.13, maturin and emsdk to be installed'
	uvx maturin build --release --target wasm32-unknown-emscripten --out dist -i 3.13
	ls -lh dist

.PHONY: format  ## Auto-format rust and python source files
format: .uv
	$(uv-run-no-sync) ruff check --fix $(sources)
	$(uv-run-no-sync) ruff format $(sources)
	cargo fmt -p $(crate)

.PHONY: lint-python  ## Lint python source files
lint-python: .uv
	$(uv-run-no-sync) ruff check $(sources)
	$(uv-run-no-sync) ruff format --check $(sources)
	$(uv-run-no-sync) griffe dump -f -d google -LWARNING -o/dev/null $(module) -s src

.PHONY: lint-rust  ## Lint rust source files
lint-rust:
	cargo fmt -p $(crate) -- --check
	cargo clippy -p $(crate) --all-targets -- -D warnings

.PHONY: lint  ## Lint rust and python source files
lint: lint-python lint-rust

.PHONY: typecheck ## Perform type-checking
typecheck: .uv
	$(uv-run-no-sync) basedpyright src tests

.PHONY: test  ## Run all tests without building the package
test:
	@$(uv-run-no-sync) pytest || (echo "pytest failed. If you see errors related to loading the extension module (.so), try running 'make test-sync' instead."; exit 1)

.PHONY: test-sync  ## Run all tests ensuring uv syncs the package beforehand
test-sync: .uv
	uv run pytest

.PHONY: test-coverage  ## Run tests and generate a coverage report
test-coverage: build-coverage
	@rm -rf htmlcov
	@mkdir -p htmlcov
	@mkdir -p $(CURDIR)/../../target/coverage
	LLVM_PROFILE_FILE="$(CURDIR)/../../target/coverage/%p-%m.profraw" $(uv-run-no-sync) coverage run -m pytest
	$(uv-run-no-sync) coverage html
	$(uv-run-no-sync) coverage report

.PHONY: benchmark  ## Run the benchmarks against an optimized build
benchmark: .uv
	$(uv-run-no-sync) maturin develop --uv --release
	$(uv-run-no-sync) pytest benchmarks --benchmark-enable --benchmark-columns=min,median,max --benchmark-sort=name

.PHONY: all  ## Format, build, lint and test this package
all: format build-dev lint test

.PHONY: clean  ## Clear local caches and build artifacts
clean:
	cargo clean -p $(crate)
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -rf .cache
	rm -rf htmlcov
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
	rm -rf dist
	find src -name '*.so' -delete

.PHONY: help  ## Display help message
help:
	@grep -E \
		'^.PHONY: .*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ".PHONY: |## "}; {printf "\033[36m%-19s\033[0m %s\n", $$2, $$3}'
