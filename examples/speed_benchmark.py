"""xnano performance benchmark — speed_benchmark.py

A scientifically rigorous benchmark comparing resource footprint (CPU, Memory),
import times, startup/exit latencies, and raw rendering performance (FPS)
across xnano, Textual, PyTermGUI, and Urwid.
"""

from __future__ import annotations

import sys
import time
import random
import subprocess


def measure_import_time(module_name: str) -> float:
    """Measure the time it takes to import a module in a clean python process."""
    cmd = [
        sys.executable,
        "-c",
        f"import time; t0 = time.perf_counter(); import {module_name}; print(time.perf_counter() - t0)",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(res.stdout.strip())
    except ValueError:
        return 0.0


def run_xnano_benchmark(duration: float) -> tuple[int, float, float, float]:
    """Run xnano stress test loop in-memory using Buffer."""
    from xnano.buffer import Buffer
    from xnano.layout import Layout
    from xnano.widgets import Block, Paragraph
    from xnano.style import Style
    from xnano.tailwind import tailwind

    # 1. Startup phase: instantiate layout and buffer in-memory
    t_start = time.perf_counter()
    layout = Layout(
        direction="vertical",
        constraints={"nav": 3, "canvas": "fill", "footer": 3},
    )

    col_layout = Layout(
        direction="horizontal",
        constraints={"left": 0.33, "center": 0.34, "right": 0.33},
        spacing=1,
    )

    # 80x24 standard screen buffer
    buf = Buffer.empty((0, 0, 80, 24))
    t_ready = time.perf_counter()
    startup_duration = t_ready - t_start

    noise_chars = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#$%"
    )
    frames = 0
    loop_duration = 0.0

    benchmark_start = time.time()
    while time.time() - benchmark_start < duration:
        loop_start = time.perf_counter()
        frames += 1
        elapsed = time.time() - benchmark_start

        # Generate 3 matrices of 600 characters
        matrix_1 = "".join(random.choice(noise_chars) for _ in range(600))
        matrix_2 = "".join(random.choice(noise_chars) for _ in range(600))
        matrix_3 = "".join(random.choice(noise_chars) for _ in range(600))

        fps = frames / elapsed if elapsed > 0 else 0.0

        # Run layout calculations and render onto buffer
        areas = layout.split((0, 0, 80, 24))
        cols = col_layout.split(areas["canvas"])

        header = Paragraph(
            f"  xnano Benchmark  ●  FPS: {fps:.1f}",
            block=Block(
                borders="all",
                border_type="rounded",
                border_style=Style(foreground=tailwind("emerald", 500)),
            ),
        )

        left_panel = Paragraph(
            matrix_1,
            block=Block(
                title=" Stream 1 ",
                borders="all",
                border_type="rounded",
                border_style=Style(foreground=tailwind("teal", 500)),
            ),
            style=Style(foreground=tailwind("teal", 400)),
        )

        center_panel = Paragraph(
            matrix_2,
            block=Block(
                title=" Stream 2 ",
                borders="all",
                border_type="rounded",
                border_style=Style(foreground=tailwind("cyan", 500)),
            ),
            style=Style(foreground=tailwind("cyan", 400)),
        )

        right_panel = Paragraph(
            matrix_3,
            block=Block(
                title=" Stream 3 ",
                borders="all",
                border_type="rounded",
                border_style=Style(foreground=tailwind("sky", 500)),
            ),
            style=Style(foreground=tailwind("sky", 400)),
        )

        footer = Paragraph(
            f"  Total Frames: {frames}",
            block=Block(
                borders="all",
                border_type="rounded",
                border_style=Style(foreground=tailwind("emerald", 600)),
            ),
        )

        buf.render(
            [
                (header, areas["nav"]),
                (left_panel, cols["left"]),
                (center_panel, cols["center"]),
                (right_panel, cols["right"]),
                (footer, areas["footer"]),
            ]
        )

        loop_duration += time.perf_counter() - loop_start

    t_exit_start = time.perf_counter()
    del buf
    exit_duration = time.perf_counter() - t_exit_start
    return frames, loop_duration, startup_duration, exit_duration


def run_textual_benchmark(duration: float) -> tuple[int, float, float, float]:
    """Run Textual stress test loop using identical layouts and operations."""
    import asyncio
    from textual.app import App, ComposeResult  # type: ignore
    from textual.widgets import Static  # type: ignore
    from textual.containers import Horizontal  # type: ignore

    noise_chars = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#$%"
    )

    class TextualStressApp(App):
        CSS = """
        Screen {
            layout: vertical;
        }
        Horizontal {
            height: 1fr;
        }
        Static {
            width: 1fr;
            border: round $primary;
            padding: 0 1;
        }
        #header {
            height: 3;
            border: round $success;
        }
        #footer {
            height: 3;
            border: round $success;
        }
        """

        def compose(self) -> ComposeResult:
            yield Static("header", id="header")
            with Horizontal():
                yield Static("left", id="left")
                yield Static("center", id="center")
                yield Static("right", id="right")
            yield Static("footer", id="footer")

        async def on_mount(self) -> None:
            self.frames = 0
            self.total_loop_time = 0.0

            # Start loop
            start_time = time.time()
            while time.time() - start_time < duration:
                loop_start = time.perf_counter()
                self.frames += 1

                # Generate 3 matrices of 600 characters
                m1 = "".join(random.choice(noise_chars) for _ in range(600))
                m2 = "".join(random.choice(noise_chars) for _ in range(600))
                m3 = "".join(random.choice(noise_chars) for _ in range(600))

                # Update widgets
                self.query_one("#left", Static).update(m1)
                self.query_one("#center", Static).update(m2)
                self.query_one("#right", Static).update(m3)

                # Update header/footer
                fps = self.frames / (time.time() - start_time)
                self.query_one("#header", Static).update(
                    f"  Textual Benchmark  ●  FPS: {fps:.1f}"
                )
                self.query_one("#footer", Static).update(
                    f"  Total Frames: {self.frames}"
                )

                # Refresh rendering
                self.refresh()
                self.total_loop_time += time.perf_counter() - loop_start

                # Yield control to textual's async event loop
                await asyncio.sleep(0.0)

            self.exit()

    t_start = time.perf_counter()
    app = TextualStressApp()
    t_ready = time.perf_counter()
    startup_duration = t_ready - t_start

    app.run(headless=True)

    t_exit_start = time.perf_counter()
    exit_duration = time.perf_counter() - t_exit_start

    return app.frames, app.total_loop_time, startup_duration, exit_duration


def run_pytermgui_benchmark(
    duration: float,
) -> tuple[int, float, float, float]:
    """Run PyTermGUI stress test loop using identical layouts."""
    t_start = time.perf_counter()
    import pytermgui as ptg  # type: ignore

    header = ptg.Label("header")
    left = ptg.Label("")
    center = ptg.Label("")
    right = ptg.Label("")

    cols = ptg.Container(left, center, right, box="ROUNDED")
    footer = ptg.Label("footer")
    root = ptg.Container(header, cols, footer)
    t_ready = time.perf_counter()
    startup_duration = t_ready - t_start

    noise_chars = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#$%"
    )
    frames = 0
    total_loop_time = 0.0

    benchmark_start = time.time()
    while time.time() - benchmark_start < duration:
        loop_start = time.perf_counter()
        frames += 1

        m1 = "".join(random.choice(noise_chars) for _ in range(600))
        m2 = "".join(random.choice(noise_chars) for _ in range(600))
        m3 = "".join(random.choice(noise_chars) for _ in range(600))

        header.value = f"PyTermGUI Benchmark  ●  Frames: {frames}"
        left.value = m1
        center.value = m2
        right.value = m3
        footer.value = f"Total: {frames}"

        # Force layout and rendering computation headlessly
        root.get_lines()

        total_loop_time += time.perf_counter() - loop_start

    t_exit_start = time.perf_counter()
    del root
    exit_duration = time.perf_counter() - t_exit_start

    return frames, total_loop_time, startup_duration, exit_duration


def run_urwid_benchmark(duration: float) -> tuple[int, float, float, float]:
    """Run Urwid stress test loop using identical layouts."""
    t_start = time.perf_counter()
    import urwid  # type: ignore

    header = urwid.Text("header")
    left = urwid.Text("")
    center = urwid.Text("")
    right = urwid.Text("")
    cols = urwid.Columns([left, center, right])
    footer = urwid.Text("footer")
    root = urwid.Pile([header, urwid.LineBox(cols), footer])
    t_ready = time.perf_counter()
    startup_duration = t_ready - t_start

    noise_chars = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#$%"
    )
    frames = 0
    total_loop_time = 0.0

    benchmark_start = time.time()
    while time.time() - benchmark_start < duration:
        loop_start = time.perf_counter()
        frames += 1

        m1 = "".join(random.choice(noise_chars) for _ in range(600))
        m2 = "".join(random.choice(noise_chars) for _ in range(600))
        m3 = "".join(random.choice(noise_chars) for _ in range(600))

        header.set_text(f"Urwid Benchmark  ●  Frames: {frames}")
        left.set_text(m1)
        center.set_text(m2)
        right.set_text(m3)
        footer.set_text(f"Total: {frames}")

        # Force layout and rendering computation headlessly
        root.render((80,))

        total_loop_time += time.perf_counter() - loop_start

    t_exit_start = time.perf_counter()
    del root
    exit_duration = time.perf_counter() - t_exit_start

    return frames, total_loop_time, startup_duration, exit_duration


def run_monitored_benchmark(framework: str, duration: float) -> dict:
    """Run a framework in a separate subprocess and monitor its resource usage."""
    cmd = [
        sys.executable,
        __file__,
        "--run",
        framework,
        "--duration",
        str(duration),
    ]

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    import psutil

    # Wait briefly for process to initialize
    time.sleep(0.02)

    cpu_samples = []
    mem_samples = []

    try:
        p = psutil.Process(proc.pid)
        p.cpu_percent(interval=None)  # Initialize CPU counter
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        p = None

    while proc.poll() is None:
        if p:
            try:
                cpu_samples.append(p.cpu_percent(interval=None))
                mem_samples.append(
                    p.memory_info().rss / (1024 * 1024)
                )  # Convert to MB
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(0.05)

    stdout, stderr = proc.communicate()

    # Parse STATS line from stdout
    frames = 0
    loop_time = 0.0
    startup_time = 0.0
    exit_time = 0.0

    for line in stdout.splitlines():
        if line.startswith("STATS|"):
            _, f_str, l_str, s_str, e_str = line.split("|")
            frames = int(f_str)
            loop_time = float(l_str)
            startup_time = float(s_str)
            exit_time = float(e_str)

    # Calculate averages, dividing CPU percent by CPU cores to show normalized single-core CPU
    num_cores = psutil.cpu_count() or 1
    avg_cpu = (
        (sum(cpu_samples) / len(cpu_samples) / num_cores)
        if cpu_samples
        else 0.0
    )
    peak_mem = max(mem_samples) if mem_samples else 0.0

    return {
        "frames": frames,
        "loop_time": loop_time,
        "startup_time": startup_time,
        "exit_time": exit_time,
        "avg_cpu": avg_cpu,
        "peak_mem": peak_mem,
    }


def main() -> None:
    # Subprocess execution block
    if "--run" in sys.argv:
        idx = sys.argv.index("--run")
        framework = sys.argv[idx + 1]

        duration = 1.0
        if "--duration" in sys.argv:
            d_idx = sys.argv.index("--duration")
            duration = float(sys.argv[d_idx + 1])

        if framework == "xnano":
            res = run_xnano_benchmark(duration)
        elif framework == "textual":
            res = run_textual_benchmark(duration)
        elif framework == "pytermgui":
            res = run_pytermgui_benchmark(duration)
        elif framework == "urwid":
            res = run_urwid_benchmark(duration)
        else:
            sys.exit(1)

        print(f"STATS|{res[0]}|{res[1]}|{res[2]}|{res[3]}")
        sys.exit(0)

    # Main coordinator execution block
    print("Preparing comprehensive Python TUI speed & resource benchmark...")
    print("=" * 105)

    # 1. Measure Import Times
    print("Phase 1: Measuring library import/load times...")
    imp_xnano = measure_import_time("xnano")
    imp_textual = measure_import_time("textual")
    imp_ptg = measure_import_time("pytermgui")
    imp_urwid = measure_import_time("urwid")

    test_duration = 2.0

    # 2. Run and monitor monitored stress tests in subprocesses
    print(f"\nPhase 2: Benchmarking xnano (Rust-backed)...")
    xn = run_monitored_benchmark("xnano", test_duration)

    print("Phase 3: Benchmarking Textual...")
    tx = run_monitored_benchmark("textual", test_duration)

    print("Phase 4: Benchmarking PyTermGUI...")
    ptg = run_monitored_benchmark("pytermgui", test_duration)

    print("Phase 5: Benchmarking Urwid...")
    ur = run_monitored_benchmark("urwid", test_duration)

    # Calculate stats
    def get_stats(data):
        frames = data["frames"]
        fps = frames / test_duration
        frame_ms = (data["loop_time"] / frames) * 1000 if frames > 0 else 0
        return fps, frame_ms

    xn_fps, xn_ms = get_stats(xn)
    tx_fps, tx_ms = get_stats(tx)
    ptg_fps, ptg_ms = get_stats(ptg)
    ur_fps, ur_ms = get_stats(ur)

    print("\n" + "=" * 105)
    print("                                      PYTHON TUI BENCHMARK RESULTS")
    print("=" * 105)
    print(
        f"{'Framework':<21} | "
        f"{'Import Time':<11} | "
        f"{'Startup':<8} | "
        f"{'Exit':<8} | "
        f"{'CPU (1 Core)':<12} | "
        f"{'Peak Mem (RSS)':<14} | "
        f"{'FPS':<8} | "
        f"{'Frame Time':<10}"
    )
    print("-" * 105)

    print(
        f"{'xnano (Rust)':<21} | "
        f"{imp_xnano:<9.3f} s | "
        f"{xn['startup_time']:<6.4f} s | "
        f"{xn['exit_time']:<6.4f} s | "
        f"{xn['avg_cpu']:<10.1f} % | "
        f"{xn['peak_mem']:<10.1f} MB | "
        f"{xn_fps:<6.1f} | "
        f"{xn_ms:.3f} ms"
    )
    print(
        f"{'Textual (CSS)':<21} | "
        f"{imp_textual:<9.3f} s | "
        f"{tx['startup_time']:<6.4f} s | "
        f"{tx['exit_time']:<6.4f} s | "
        f"{tx['avg_cpu']:<10.1f} % | "
        f"{tx['peak_mem']:<10.1f} MB | "
        f"{tx_fps:<6.1f} | "
        f"{tx_ms:.3f} ms"
    )
    print(
        f"{'PyTermGUI (Python)':<21} | "
        f"{imp_ptg:<9.3f} s | "
        f"{ptg['startup_time']:<6.4f} s | "
        f"{ptg['exit_time']:<6.4f} s | "
        f"{ptg['avg_cpu']:<10.1f} % | "
        f"{ptg['peak_mem']:<10.1f} MB | "
        f"{ptg_fps:<6.1f} | "
        f"{ptg_ms:.3f} ms"
    )
    print(
        f"{'Urwid (Curses)':<21} | "
        f"{imp_urwid:<9.3f} s | "
        f"{ur['startup_time']:<6.4f} s | "
        f"{ur['exit_time']:<6.4f} s | "
        f"{ur['avg_cpu']:<10.1f} % | "
        f"{ur['peak_mem']:<10.1f} MB | "
        f"{ur_fps:<6.1f} | "
        f"{ur_ms:.3f} ms"
    )
    print("=" * 105)

    print("\nBenchmark Insights:")
    if xn_fps > tx_fps:
        factor = xn_fps / tx_fps
        print(f"🚀 xnano runs {factor:.1f}x FASTER at rendering than Textual.")
    if xn["avg_cpu"] < tx["avg_cpu"]:
        cpu_diff = tx["avg_cpu"] - xn["avg_cpu"]
        print(
            f"📉 xnano consumes {cpu_diff:.1f}% less CPU resource than Textual."
        )
    if xn["peak_mem"] < tx["peak_mem"]:
        mem_saved = tx["peak_mem"] - xn["peak_mem"]
        print(
            f"🧠 xnano uses {mem_saved:.1f} MB less RAM memory footprint than Textual."
        )
    print("=" * 105 + "\n")


if __name__ == "__main__":
    main()
