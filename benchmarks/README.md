# benchmarks

Performance benchmarks for `xnano`, measured continuously in CI by
[CodSpeed](https://codspeed.io).

These live outside `tests/` on purpose: a bare `pytest` run only collects
`tests/` (see `testpaths` in `pyproject.toml`), so the benchmark suite never
slows the correctness suite down. It is opted into explicitly.

## Running locally

Plain timings through `pytest-benchmark`:

```bash
uv run pytest benchmarks
```

CodSpeed CPU simulation, the same measurement CI performs (needs the
[CodSpeed CLI](https://codspeed.io/docs/cli)):

```bash
uv run codspeed run --mode simulation -- pytest benchmarks --codspeed
```

## Layout

| File                    | What it measures                                                              |
| ----------------------- | ----------------------------------------------------------------------------- |
| `test_markup.py`        | Markdown tokenization, code highlighting, ANSI decoding                       |
| `test_styles.py`        | Tailwind class resolution, color parsing, native color bridging               |
| `test_components.py`    | Component construction and `compose()` for text, tables, charts, bars, options |
| `test_rendering.py`     | Content lowering and full offscreen frames through `Runtime` and `render()`    |
| `test_interaction.py`   | Keyboard input, focus navigation, reactive hooks, form and search flows        |

## Adding a benchmark

Use the `benchmark` fixture and keep everything that is not the hot path out of
the measured callable:

```python
def _work(subject: Subject) -> object:
    return subject.hot_path()


def test_hot_path(benchmark) -> None:
    subject = Subject()
    result = benchmark(_work, subject)
    assert result is not None
```

Two things to watch for in this codebase:

- Several parsers are `functools.lru_cache`-backed. Call `cache_clear()` as the
  first statement of the measured callable or you will benchmark a dict lookup.
- CodSpeed calls the measured callable more than once, so it must be
  idempotent. Reset any mutated state at the top of the callable.
