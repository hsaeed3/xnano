"""xnano example — feed.py

Real-time API health monitor. Four services tracked live with:
  · btop-style filled-area canvas graph for the selected service
  · per-service sparklines for at-a-glance comparison
  · service health table + error-rate gauges
  · endpoint hit distribution (BarChartNode, right panel)
  · live HTTP request log (scrolling TableNode, bottom panel)
"""

from __future__ import annotations

import dataclasses
import random
import time

from xnano.beta import Field, Grid, Terminal, on_keyboard, on_tick
from xnano.beta.components import Sparkline, Text
from xnano.beta.components.abstract import AbstractComponent, ComponentRenderContext
from xnano.beta.color import ColorLike, tailwind_color


# ── Services & palette ────────────────────────────────────────────────────────

_SERVICES = ["api", "cache", "db", "worker"]

_SVC_COLORS = {
    "api":    tailwind_color("sky",    400),
    "cache":  tailwind_color("teal",   400),
    "db":     tailwind_color("violet", 400),
    "worker": tailwind_color("amber",  400),
}

_SVC_TEXT = {
    "api":    tailwind_color("sky",    500),
    "cache":  tailwind_color("teal",   500),
    "db":     tailwind_color("violet", 500),
    "worker": tailwind_color("amber",  500),
}

_SVC_FILL = {
    "api":    tailwind_color("sky",    800),
    "cache":  tailwind_color("teal",   800),
    "db":     tailwind_color("violet", 800),
    "worker": tailwind_color("amber",  800),
}

_STATUS_LABELS = {
    "ok":   ("●", tailwind_color("emerald", 400)),
    "warn": ("◆", tailwind_color("amber",   400)),
    "crit": ("✖", tailwind_color("rose",    500)),
}

_HISTORY_LEN = 80
_LOG_LEN     = 9

_ENDPOINTS = {
    "api":    ["/v2/users", "/v2/auth", "/v2/sessions", "/v2/profile", "/v2/metrics"],
    "cache":  ["/get", "/set", "/invalidate", "/ttl"],
    "db":     ["/query", "/insert", "/update", "/health"],
    "worker": ["/submit", "/status", "/cancel", "/queue"],
}
_METHODS = {
    "api":    ["GET", "GET", "GET", "POST", "DELETE"],
    "cache":  ["GET", "GET", "POST"],
    "db":     ["GET", "GET", "POST", "PUT"],
    "worker": ["POST", "GET", "GET"],
}
_METHOD_COLORS = {
    "GET":    tailwind_color("sky",    400),
    "POST":   tailwind_color("violet", 400),
    "PUT":    tailwind_color("amber",  400),
    "DELETE": tailwind_color("rose",   400),
}
_BASE_LATENCY = {"api": 42, "cache": 4, "db": 78, "worker": 185}


def _color_hex(c) -> str:
    return f"#{c.r:02x}{c.g:02x}{c.b:02x}"


# ── Simulated metrics ─────────────────────────────────────────────────────────

_BASES_RPS = {"api": 280.0, "cache": 510.0, "db": 120.0, "worker": 75.0}
_BASES_ERR = {"api": 0.8,   "cache": 0.3,   "db":  1.2,  "worker": 2.1}


def _smooth(data: list[float], alpha: float = 0.14) -> list[float]:
    if len(data) < 2:
        return data
    fwd = [data[0]]
    for v in data[1:]:
        fwd.append(alpha * v + (1 - alpha) * fwd[-1])
    bwd = [fwd[-1]]
    for v in reversed(fwd[:-1]):
        bwd.append(alpha * v + (1 - alpha) * bwd[-1])
    return list(reversed(bwd))


def _seed_rps() -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for svc, base in _BASES_RPS.items():
        s: list[float] = [base]
        for _ in range(_HISTORY_LEN - 1):
            s.append(max(0.0, s[-1] + random.gauss(0, base * 0.02)))
        out[svc] = _smooth(s)
    return out


def _seed_err() -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for svc, base in _BASES_ERR.items():
        s: list[float] = [base]
        for _ in range(_HISTORY_LEN - 1):
            s.append(max(0.0, min(20.0, s[-1] + random.gauss(0, 0.10))))
        out[svc] = _smooth(s)
    return out


def _service_status(err_pct: float) -> str:
    if err_pct < 2.0:
        return "ok"
    if err_pct < 8.0:
        return "warn"
    return "crit"


def _gen_event(svc: str, err_pct: float) -> tuple:
    method   = random.choice(_METHODS[svc])
    endpoint = f"/{svc}{random.choice(_ENDPOINTS[svc])}"
    if random.random() < err_pct / 100.0:
        status = random.choice([400, 404, 429, 500, 503])
    else:
        status = {"GET": 200, "POST": 201, "DELETE": 204}.get(method, 200)
    base = _BASE_LATENCY[svc]
    latency = base * random.randint(3, 8) if status >= 500 else max(1, int(base * random.gauss(1.0, 0.3)))
    return (time.strftime("%H:%M:%S"), method, endpoint, status, latency, svc)


def _build_spark(history: list[float], color) -> Sparkline:
    n    = _HISTORY_LEN
    data = [int(v) for v in (history[-n:] if len(history) >= n else [0] * (n - len(history)) + history)]
    return Sparkline(data=data, color=_color_hex(color), max_value=max(max(data), 1))


# ── Custom components ─────────────────────────────────────────────────────────

@dataclasses.dataclass
class ServiceGraph(AbstractComponent):
    data: list = dataclasses.field(default_factory=list)
    fill_color: object = dataclasses.field(default=None)
    edge_color: object = dataclasses.field(default=None)
    max_v: float = 1.0
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    def get_node(self, ctx: ComponentRenderContext):  # type: ignore[override]
        from xnano.beta.core.nodes import CanvasLine, CanvasNode, CanvasPrint, SpanNode

        smoothed = _smooth(self.data, alpha=0.12)
        n = len(smoothed)
        if n < 2:
            return CanvasNode(shapes=[], x_bounds=(0.0, 1.0), y_bounds=(0.0, 1.0))

        fill_hex = _color_hex(self.fill_color or tailwind_color("sky", 800))
        edge_hex = _color_hex(self.edge_color or tailwind_color("sky", 400))
        max_v    = max(self.max_v, 1.0)
        axis_c   = tailwind_color("slate", 600)
        shapes   = []

        for i, v in enumerate(smoothed):
            if v > 0.0:
                shapes.append(CanvasLine(x1=float(i), y1=0.0, x2=float(i), y2=v, color=fill_hex))

        for i in range(1, n):
            shapes.append(CanvasLine(
                x1=float(i - 1), y1=smoothed[i - 1],
                x2=float(i),     y2=smoothed[i],
                color=edge_hex,
            ))

        for frac in (0.25, 0.5, 0.75, 1.0):
            val = max_v * frac
            shapes.append(CanvasPrint(
                x=0.5, y=val,
                content=SpanNode(
                    content=f"{val:.0f}" if max_v >= 10 else f"{val:.1f}",
                    color=axis_c,
                ),
            ))

        return CanvasNode(
            shapes=shapes,
            x_bounds=(0.0, float(n - 1)),
            y_bounds=(0.0, max_v * 1.05),
            marker="half_block",
        )


@dataclasses.dataclass
class ServiceTable(AbstractComponent):
    rows: list = dataclasses.field(default_factory=list)
    selected: int = 0
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    def get_node(self, ctx: ComponentRenderContext):  # type: ignore[override]
        from xnano.beta.core.nodes import SpanNode, TableCellItem, TableNode, TableRowItem

        dim    = tailwind_color("slate", 500)
        header = TableRowItem(cells=[
            TableCellItem(content="",          color=dim),
            TableCellItem(content=" Service ", color=dim),
            TableCellItem(content=" RPS  ",   color=dim),
            TableCellItem(content=" Err% ",   color=dim),
            TableCellItem(content=" p95 ",    color=dim),
        ], height=1)

        tbl_rows = []
        for svc, rps, err_pct, p95, status in self.rows:
            sym, sc = _STATUS_LABELS[status]
            err_c = (tailwind_color("emerald", 400) if err_pct < 2.0
                     else tailwind_color("amber", 400) if err_pct < 8.0
                     else tailwind_color("rose",  500))
            tbl_rows.append(TableRowItem(cells=[
                TableCellItem(content=SpanNode(content=f" {sym} ", color=sc, modifiers=["bold"])),
                TableCellItem(content=SpanNode(content=f" {svc:<7}", color=_SVC_TEXT[svc], modifiers=["bold"])),
                TableCellItem(content=f" {rps:>5.0f} ",   color=tailwind_color("slate", 600)),
                TableCellItem(content=SpanNode(content=f" {err_pct:>4.1f}% ", color=err_c)),
                TableCellItem(content=f" {p95:>3.0f}ms",  color=tailwind_color("slate", 600)),
            ], height=1))

        return TableNode(
            rows=tbl_rows,
            header=header,
            column_widths=[0.06, 0.26, 0.20, 0.24, 0.24],
            column_spacing=0,
            selected_row=self.selected,
            highlight_background=tailwind_color("slate", 700),
            highlight_color="white",
        )


@dataclasses.dataclass
class ErrorGauge(AbstractComponent):
    service: str = ""
    ratio: float = 0.0
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    def get_node(self, ctx: ComponentRenderContext):  # type: ignore[override]
        from xnano.beta.core.nodes import LineGaugeNode

        if self.ratio < 0.02:
            filled = tailwind_color("emerald", 500)
        elif self.ratio < 0.08:
            filled = tailwind_color("amber",   400)
        else:
            filled = tailwind_color("rose",    500)

        return LineGaugeNode(
            progress=min(1.0, self.ratio / 0.20),
            label=f"  {self.service:<7}  {self.ratio * 100:.1f}%",
            filled_color=filled,
            unfilled_color=tailwind_color("slate", 500),
            color=tailwind_color("slate", 700),
        )


@dataclasses.dataclass
class EndpointChart(AbstractComponent):
    """Bar chart of top-5 endpoints by request count for the selected service."""

    endpoints: list = dataclasses.field(default_factory=list)
    accent: ColorLike | None = dataclasses.field(default=None)
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    def get_node(self, ctx: ComponentRenderContext):  # type: ignore[override]
        from xnano.beta.core.nodes import BarChartNode, BarGroupItem, BarItem

        if not self.endpoints:
            return BarChartNode(groups=[], direction="vertical", max_value=1)

        max_v = max(count for _, count in self.endpoints) or 1
        c     = self.accent or tailwind_color("sky", 500)

        groups = [
            BarGroupItem(bars=[BarItem(value=count, label=label[:7], color=c)])
            for label, count in self.endpoints
        ]
        return BarChartNode(
            groups=groups,
            bar_width=5,
            bar_gap=0,
            group_gap=2,
            max_value=max_v,
            direction="vertical",
            label_color=tailwind_color("slate", 600),
        )


@dataclasses.dataclass
class EventLog(AbstractComponent):
    """Scrolling table of recent HTTP requests with colour-coded status/latency."""

    events: list = dataclasses.field(default_factory=list)
    fit_content: bool = dataclasses.field(default=False, kw_only=True)

    def get_node(self, ctx: ComponentRenderContext):  # type: ignore[override]
        from xnano.beta.core.nodes import SpanNode, TableCellItem, TableNode, TableRowItem

        dim    = tailwind_color("slate", 500)
        header = TableRowItem(cells=[
            TableCellItem(content=" Time    ", color=dim),
            TableCellItem(content=" Method ", color=dim),
            TableCellItem(content=" Endpoint                  ", color=dim),
            TableCellItem(content=" Status ", color=dim),
            TableCellItem(content=" Latency ", color=dim),
            TableCellItem(content=" Service ", color=dim),
        ], height=1)

        rows = []
        for ts, method, endpoint, status, latency, svc in self.events:
            sc = (tailwind_color("emerald", 400) if status < 300
                  else tailwind_color("amber",   400) if status < 500
                  else tailwind_color("rose",    400))
            lc = (tailwind_color("emerald", 400) if latency < 50
                  else tailwind_color("amber",   400) if latency < 200
                  else tailwind_color("rose",    400))
            mc = _METHOD_COLORS.get(method, tailwind_color("slate", 500))

            rows.append(TableRowItem(cells=[
                TableCellItem(content=f" {ts}  ",                           color=tailwind_color("slate", 600)),
                TableCellItem(content=SpanNode(content=f" {method:<6} ",    color=mc)),
                TableCellItem(content=f" {endpoint:<28}",                   color=tailwind_color("slate", 600)),
                TableCellItem(content=SpanNode(content=f"  {status}  ",     color=sc, modifiers=["bold"])),
                TableCellItem(content=SpanNode(content=f" {latency:>5}ms ", color=lc)),
                TableCellItem(content=SpanNode(content=f" {svc:<8}",        color=_SVC_TEXT[svc])),
            ], height=1))

        return TableNode(
            rows=rows,
            header=header,
            column_widths=[0.12, 0.09, 0.34, 0.10, 0.14, 0.21],
            column_spacing=0,
        )


# ── Layout ────────────────────────────────────────────────────────────────────

class SparkRow(Grid, direction="horizontal", gap=1):
    s_api:    Sparkline = Field(default_factory=Sparkline, border="plain",
                                border_color=tailwind_color("sky",    700), title=" api ")
    s_cache:  Sparkline = Field(default_factory=Sparkline, border="plain",
                                border_color=tailwind_color("teal",   700), title=" cache ")
    s_db:     Sparkline = Field(default_factory=Sparkline, border="plain",
                                border_color=tailwind_color("violet", 700), title=" db ")
    s_worker: Sparkline = Field(default_factory=Sparkline, border="plain",
                                border_color=tailwind_color("amber",  700), title=" worker ")


class GaugeStack(Grid, direction="vertical", gap=0):
    g0: ErrorGauge = Field(default_factory=ErrorGauge, height=3,
                           border="plain", border_color=tailwind_color("slate", 800))
    g1: ErrorGauge = Field(default_factory=ErrorGauge, height=3,
                           border="plain", border_color=tailwind_color("slate", 800))
    g2: ErrorGauge = Field(default_factory=ErrorGauge, height=3,
                           border="plain", border_color=tailwind_color("slate", 800))
    g3: ErrorGauge = Field(default_factory=ErrorGauge, height=3,
                           border="plain", border_color=tailwind_color("slate", 800))


class RightPanel(Grid, direction="vertical", gap=1):
    table: ServiceTable = Field(
        default_factory=ServiceTable,
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" Services ",
    )
    gauges: GaugeStack = Field(
        default_factory=GaugeStack,
        height=12,
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" Error Rate ",
    )
    endpoint_chart: EndpointChart = Field(
        default_factory=EndpointChart,
        height=14,
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" Top Endpoints ",
    )


class GraphPanel(Grid, direction="vertical", gap=1):
    svc_label: Text = Field(default=Text(""), height=1)
    main_graph: ServiceGraph = Field(
        default_factory=ServiceGraph,
        border="rounded",
        border_color=tailwind_color("sky", 800),
        title=" Requests / sec ",
    )
    sparks: SparkRow = Field(
        default_factory=SparkRow,
        height=5,
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" All Services ",
    )
    event_log: EventLog = Field(
        default_factory=EventLog,
        height=11,
        border="rounded",
        border_color=tailwind_color("slate", 700),
        title=" Live Requests ",
    )


class MainArea(Grid, direction="horizontal", gap=1):
    graphs: GraphPanel = Field(default_factory=GraphPanel, width="62%")
    right:  RightPanel = Field(default_factory=RightPanel)


class ApiMonitor(Grid, direction="vertical"):
    header: str = Field(
        default="  API HEALTH MONITOR",
        height=1,
        color=tailwind_color("sky", 500),
        modifiers=["bold"],
    )
    main: MainArea = Field(default_factory=MainArea)
    footer: str = Field(
        default="  [↑↓] Select service  [q] Quit",
        height=1,
        color=tailwind_color("slate", 600),
    )

    rps_history:   dict = Field(default_factory=_seed_rps, state=True)
    err_history:   dict = Field(default_factory=_seed_err, state=True)
    selected:      int  = Field(default=0, state=True)
    p95:           dict = Field(
        default_factory=lambda: {"api": 42.0, "cache": 8.0, "db": 94.0, "worker": 210.0},
        state=True,
    )
    event_log:     list = Field(default_factory=list, state=True)
    endpoint_hits: dict = Field(
        default_factory=lambda: {svc: {} for svc in _SERVICES},
        state=True,
    )

    @on_keyboard("up")
    def _up(self) -> None:
        self.selected = (self.selected - 1) % len(_SERVICES)

    @on_keyboard("down")
    def _down(self) -> None:
        self.selected = (self.selected + 1) % len(_SERVICES)

    @on_keyboard("q")
    def _quit(self, ctx) -> None:
        ctx.terminal.request_exit()

    @on_tick(500)
    def _tick(self) -> None:
        rps  = {svc: list(v) for svc, v in self.rps_history.items()}
        err  = {svc: list(v) for svc, v in self.err_history.items()}
        p95  = dict(self.p95)
        hits = {svc: dict(h) for svc, h in self.endpoint_hits.items()}
        new_events: list = []

        for svc in _SERVICES:
            rps[svc].append(max(0.0, rps[svc][-1] + random.gauss(0, _BASES_RPS[svc] * 0.02)))
            err[svc].append(max(0.0, min(20.0, err[svc][-1] + random.gauss(0, 0.10))))
            p95[svc] = max(1.0, p95[svc] + random.gauss(0, 2.0))
            if len(rps[svc]) > _HISTORY_LEN:
                rps[svc].pop(0)
            if len(err[svc]) > _HISTORY_LEN:
                err[svc].pop(0)

            for _ in range(random.randint(1, 3)):
                ev = _gen_event(svc, err[svc][-1])
                new_events.append(ev)
                ep = ev[2]
                hits[svc][ep] = hits[svc].get(ep, 0) + 1

        self.rps_history   = rps
        self.err_history   = err
        self.p95           = p95
        self.endpoint_hits = hits
        self.event_log     = (self.event_log + new_events)[-_LOG_LEN:]

    def grid_render(self) -> None:
        rps     = self.rps_history
        err     = self.err_history
        p95     = self.p95
        sel_svc = _SERVICES[self.selected]

        # Main filled-area graph
        max_rps = max(max(v) for v in rps.values()) * 1.1
        self.main.graphs.main_graph = ServiceGraph(
            data=rps[sel_svc],
            fill_color=_SVC_FILL[sel_svc],
            edge_color=_SVC_COLORS[sel_svc],
            max_v=max_rps,
        )

        # Service label strip
        rps_now = rps[sel_svc][-1]
        err_now = err[sel_svc][-1]
        self.main.graphs.svc_label = Text([
            Text(f"  {sel_svc.upper()}  ", color=_SVC_TEXT[sel_svc], modifiers=("bold",)),
            Text(
                f"{rps_now:.0f} rps  ·  {err_now:.1f}% err  ·  {p95[sel_svc]:.0f}ms p95",
                color=tailwind_color("slate", 500),
            ),
        ])

        # Sparklines
        sp = self.main.graphs.sparks
        sp.s_api    = _build_spark(rps["api"],    _SVC_COLORS["api"])
        sp.s_cache  = _build_spark(rps["cache"],  _SVC_COLORS["cache"])
        sp.s_db     = _build_spark(rps["db"],     _SVC_COLORS["db"])
        sp.s_worker = _build_spark(rps["worker"], _SVC_COLORS["worker"])

        # Event log
        self.main.graphs.event_log = EventLog(events=list(self.event_log))

        # Service table
        tbl_rows = [
            (svc, rps[svc][-1], err[svc][-1], p95[svc], _service_status(err[svc][-1]))
            for svc in _SERVICES
        ]
        self.main.right.table = ServiceTable(rows=tbl_rows, selected=self.selected)

        # Error gauges
        g = self.main.right.gauges
        for attr, svc in zip(("g0", "g1", "g2", "g3"), _SERVICES):
            setattr(g, attr, ErrorGauge(service=svc, ratio=err[svc][-1] / 100.0))

        # Endpoint chart for selected service
        sel_hits = self.endpoint_hits[sel_svc]
        top_eps  = sorted(sel_hits.items(), key=lambda x: x[1], reverse=True)[:5]
        ep_data  = [(ep.split("/")[-1][:8], cnt) for ep, cnt in top_eps]
        self.main.right.endpoint_chart = EndpointChart(
            endpoints=ep_data,
            accent=_SVC_COLORS[sel_svc],
        )

        # Header
        total_rps = sum(v[-1] for v in rps.values())
        alerts    = sum(1 for svc in _SERVICES if _service_status(err[svc][-1]) != "ok")
        self.header = (
            f"  API HEALTH MONITOR  ·  {total_rps:.0f} rps total  ·  "
            f"{'● all healthy' if not alerts else f'✖ {alerts} alert(s)'}  ·  "
            f"{time.strftime('%H:%M:%S')}"
        )
        self.footer = f"  [↑↓] cycle service  ·  showing: {sel_svc}  ·  [q] Quit"


if __name__ == "__main__":
    Terminal(tick_interval=500).run(ApiMonitor())
