"""Live stats dashboard screen."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Select, Static


def _fmt_hms(seconds: float) -> str:
    s = int(seconds)
    h, m = divmod(s, 3600)
    m, s = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _fmt_mb(path: Path) -> str:
    try:
        size_mb = path.stat().st_size / (1024 * 1024)
        return f"{size_mb:.1f} MB"
    except (OSError, AttributeError):
        return "N/A"


@dataclass
class _DashboardSnapshot:

    req_count: int = 0
    req_rate: float = 0.0
    uptime_seconds: float = 0.0
    active_threads: int = 0
    max_workers: int = 0
    queue_size: int = 0
    db_size: str = ""
    db_rows: int = 0
    local_url: str = ""
    api_url: str = ""
    upstream_url: str = ""
    ollama_url: str = ""


DASH_CONFIG_FIELDS = [
    ("thinking", "thinking", "Thinking", [
        ("Enabled", "enabled"), ("Disabled", "disabled"),
    ]),
    ("reasoning_effort", "reasoning_effort", "Effort", [
        ("Low", "low"), ("Medium", "medium"), ("High", "high"),
        ("Max", "max"), ("XHigh", "xhigh"),
    ]),
    ("display_reasoning", "display_reasoning", "Show Think", [
        ("On", "true"), ("Off", "false"),
    ]),
    ("ngrok", "ngrok", "Ngrok", [
        ("On", "true"), ("Off", "false"),
    ]),
]


class DashboardScreen(Horizontal):
    """Live statistics for the proxy server."""

    _prev_req_count: int = 0
    _prev_snapshot_time: float = 0.0

    def compose(self) -> ComposeResult:
        with Vertical(id="dashboard-left"):
            with Vertical(id="dashboard-stats"):
                yield Static("Connecting...", id="dashboard-text")
        with Vertical(id="dashboard-right"):
            yield Static("[bold]Quick Config[/]", id="dash-config-title")
            for widget_id, _attr, label, options in DASH_CONFIG_FIELDS:
                yield Select(
                    options,
                    prompt=label,
                    id=f"dash-{widget_id}",
                    allow_blank=False,
                )
            yield Button("Apply", id="dash-apply", variant="primary")

    def on_mount(self) -> None:
        self._prev_snapshot_time = time.monotonic()
        self.set_interval(1.0, self.refresh_stats)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "dash-apply":
            return
        config = getattr(self.app, "server_config", None)
        if config is None:
            return
        updates = {}
        for widget_id, attr, _label, _options in DASH_CONFIG_FIELDS:
            try:
                widget = self.query_one(f"#dash-{widget_id}", Select)
            except Exception:
                continue
            raw = str(widget.value)
            if raw in ("true", "false"):
                updates[attr] = raw == "true"
            else:
                updates[attr] = raw
        try:
            self.app.server_config = replace(config, **updates)
        except (TypeError, ValueError):
            pass

    def refresh_stats(self) -> None:
        app = self.app
        server = getattr(app, "server", None)
        if server is None:
            return

        snap = _DashboardSnapshot()
        snap.req_count = getattr(server, "request_count", 0)
        now = time.monotonic()
        elapsed = now - self._prev_snapshot_time
        if elapsed > 0:
            snap.req_rate = (snap.req_count - self._prev_req_count) / elapsed
        self._prev_req_count = snap.req_count
        self._prev_snapshot_time = now

        start: float = getattr(server, "start_time", 0.0)
        snap.uptime_seconds = max(0.0, now - start) if start > 0 else 0.0

        executor = getattr(server, "executor", None)
        if executor is not None:
            try:
                snap.active_threads = len(executor._threads)
            except Exception:
                snap.active_threads = -1
            try:
                snap.max_workers = executor._max_workers
            except Exception:
                snap.max_workers = -1
            try:
                snap.queue_size = executor._work_queue.qsize()
            except Exception:
                snap.queue_size = -1
        else:
            snap.active_threads = -1
            snap.max_workers = -1
            snap.queue_size = -1

        store = getattr(server, "reasoning_store", None)
        if store is not None:
            db_path = getattr(store, "reasoning_content_path", None)
            if isinstance(db_path, Path):
                snap.db_size = _fmt_mb(db_path)
                try:
                    row = store._conn.execute(
                        "SELECT COUNT(*) FROM reasoning_cache"
                    ).fetchone()
                    snap.db_rows = row[0] if row else 0
                except Exception:
                    snap.db_rows = -1
            else:
                snap.db_size = "in-memory"
                snap.db_rows = -1
        else:
            snap.db_size = "N/A"
            snap.db_rows = -1

        config = getattr(server, "config", None)
        if config:
            host = config.host or "127.0.0.1"
            port = config.port or 9000
            snap.local_url = f"http://{host}:{port}/v1"
            public_url = getattr(server, "public_url", None)
            snap.api_url = (
                f"{public_url.rstrip('/')}/v1" if public_url else snap.local_url
            )
            snap.upstream_url = f"{config.upstream_base_url}/chat/completions"
            snap.ollama_url = f"http://{host}:{port}"

        lines: list[str] = []
        lines.append(
            f"  [bold]Requests[/]     {snap.req_count:,} total  |  {snap.req_rate:.1f} req/s"
        )
        lines.append(
            f"  [bold]Thread Pool[/]  {snap.active_threads}/{snap.max_workers}"
            f" active  |  queue: {snap.queue_size}"
        )
        lines.append(
            f"  [bold]DB[/]           {snap.db_size}  |  {snap.db_rows:,} rows"
        )
        lines.append(f"  [bold]Uptime[/]       {_fmt_hms(snap.uptime_seconds)}")

        if snap.local_url:
            lines.append("")
            lines.append("[bold]Connection[/]")
            lines.append(f"  Cursor Base URL: {snap.api_url}")
            lines.append(f"  Upstream:        {snap.upstream_url}")
            lines.append(f"  Ollama:          {snap.ollama_url}")

        self.query_one("#dashboard-text", Static).update("\n".join(lines))

        if config:
            for widget_id, attr, _label, _options in DASH_CONFIG_FIELDS:
                try:
                    widget = self.query_one(f"#dash-{widget_id}", Select)
                except Exception:
                    continue
                raw = getattr(config, attr, "")
                if isinstance(raw, bool):
                    raw = "true" if raw else "false"
                try:
                    widget.value = str(raw)
                except Exception:
                    pass
