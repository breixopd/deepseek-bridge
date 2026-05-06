"""Config editor screen -- view and edit proxy configuration."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Button, Input, Label, Select, Static

SELECT_FIELDS = [
    ("thinking", "thinking", "Thinking", "Model", [
        ("Enabled", "enabled"), ("Disabled", "disabled"),
    ]),
    ("reasoning_effort", "reasoning_effort", "Reasoning Effort", "Model", [
        ("Low", "low"), ("Medium", "medium"), ("High", "high"),
        ("Max", "max"), ("XHigh", "xhigh"),
    ]),
    ("display_reasoning", "display_reasoning", "Show Reasoning", "Model", [
        ("On", "true"), ("Off", "false"),
    ]),
    ("collapsible_reasoning", "collapsible_reasoning", "Collapsible", "Model", [
        ("On", "true"), ("Off", "false"),
    ]),
    ("host", "host", "Host", "Network", None),
    ("port", "port", "Port", "Network", None),
    ("ngrok", "ngrok", "Ngrok", "Network", [
        ("On", "true"), ("Off", "false"),
    ]),
    ("cors", "cors", "CORS", "Network", [
        ("On", "true"), ("Off", "false"),
    ]),
    ("ollama", "ollama", "Ollama", "Network", [
        ("On", "true"), ("Off", "false"),
    ]),
    ("verbose", "verbose", "Verbose", "Storage", [
        ("On", "true"), ("Off", "false"),
    ]),
    ("compact", "compact", "Compact", "Storage", [
        ("On", "true"), ("Off", "false"),
    ]),
    ("request_timeout", "request_timeout", "Req Timeout (s)", "Storage", None),
    ("log_dir", "log_dir", "Log Dir", "Storage", None),
]


class ConfigScreen(VerticalScroll, can_focus=True):
    """View and edit proxy configuration at runtime."""

    def compose(self) -> ComposeResult:
        yield Static("[bold]Configuration[/] -- edit and apply changes", id="config-title")
        yield Static("", id="config-status")

        for category in ("Model", "Network", "Storage"):
            with VerticalScroll(classes="config-group") as group:
                group.border_title = category
                yield from self._category_widgets(category)

        yield Button("Apply Changes", id="save-btn", variant="primary")

    def _category_widgets(self, category: str):
        for widget_id, attr, label, cat, options in SELECT_FIELDS:
            if cat != category:
                continue
            yield Label(f" {label}")
            if options is not None:
                yield Select(
                    options,
                    prompt=label,
                    id=f"cfg-{widget_id}",
                    allow_blank=False,
                )
            else:
                yield Input(
                    placeholder=label,
                    id=f"cfg-{widget_id}",
                )

    def on_mount(self) -> None:
        self._populate()

    def _populate(self) -> None:
        config = getattr(self.app, "server_config", None)
        if config is None:
            return
        for widget_id, attr, _label, _cat, options in SELECT_FIELDS:
            try:
                widget = self.query_one(f"#cfg-{widget_id}")
            except Exception:
                continue
            value = str(getattr(config, attr, ""))
            if value is None or value == "None":
                value = ""
            if options is not None and isinstance(widget, Select):
                if value in {"true", "false"}:
                    widget.value = "true" if value == "true" else "false"
                else:
                    widget.value = value
            elif isinstance(widget, Input):
                widget.value = value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "save-btn":
            return
        config = getattr(self.app, "server_config", None)
        if config is None:
            self._status("No configuration available")
            return

        updates: dict[str, Any] = {}
        for widget_id, attr, _label, _cat, options in SELECT_FIELDS:
            try:
                widget = self.query_one(f"#cfg-{widget_id}")
            except Exception:
                continue

            if isinstance(widget, Select):
                raw = str(widget.value)
            elif isinstance(widget, Input):
                raw = widget.value.strip()
            else:
                continue

            if raw == "" and widget_id == "log_dir":
                updates[attr] = None
                continue

            if options is not None and isinstance(widget, Select):
                if raw in ("true", "false"):
                    updates[attr] = raw == "true"
                else:
                    updates[attr] = raw
                continue

            if widget_id == "port":
                try:
                    updates[attr] = int(raw) if raw else int(config.port)
                except ValueError:
                    self._status(f"Invalid port: {raw}")
                    return
                continue

            if widget_id == "request_timeout":
                try:
                    updates[attr] = float(raw) if raw else float(config.request_timeout)
                except ValueError:
                    self._status(f"Invalid timeout: {raw}")
                    return
                continue

            updates[attr] = raw

        try:
            self.app.server_config = replace(config, **updates)  # type: ignore[attr-defined]
            self._status("Applied -- some changes may require restart")
        except (TypeError, ValueError) as exc:
            self._status(f"Error: {exc}")

    def _status(self, msg: str) -> None:
        try:
            self.query_one("#config-status", Static).update(msg)
        except Exception:
            pass
