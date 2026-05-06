"""TUI Dashboard application."""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, TabbedContent, TabPane

from .config import ConfigScreen
from .dashboard import DashboardScreen
from .logs import LogsScreen


class TuiApp(App[None]):
    """Textual TUI dashboard for deepseek-bridge."""

    TITLE = "DeepSeek Bridge"

    CSS = """
    TabbedContent { height: 1fr; }
    TabPane { height: 1fr; }
    Screen { overflow-y: auto; }
    ConfigScreen { height: 1fr; }
    .config-group {
        border: solid $primary;
        margin: 0 1 1 1;
        padding: 1 2;
        height: auto;
    }
    Label { width: 100%; padding-top: 1; }
    Select { width: 1fr; margin-bottom: 1; }
    Input { width: 1fr; margin-bottom: 1; }
    #config-title { padding: 1 2; }
    #config-status { padding: 0 2; height: 1; }
    #save-btn { margin: 1 0 2 0; min-height: 3; }
    DashboardScreen { height: 1fr; }
    #dashboard-left { width: 2fr; padding: 1 2; }
    #dashboard-right {
        width: 1fr;
        padding: 1 2;
        border-left: solid $primary;
    }
    """

    def __init__(
        self,
        server_config: Any = None,
        server: Any = None,
    ) -> None:
        super().__init__()
        self.server_config = server_config
        self.server = server

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent("Dashboard", "Config", "Logs"):
            with TabPane("Dashboard"):
                yield DashboardScreen()
            with TabPane("Config"):
                yield ConfigScreen()
            with TabPane("Logs"):
                yield LogsScreen()
        yield Footer()
