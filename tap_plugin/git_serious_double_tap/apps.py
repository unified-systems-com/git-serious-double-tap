"""git-serious double-tap plugin AppConfig — the base ready() registers the manifest; this one
adds the plugin's own panel type (req-git-serious-double-tap-page-strip)."""

from tap_plugins.base import TapPluginConfig


class GitSeriousDoubleTapConfig(TapPluginConfig):
    def ready(self) -> None:
        super().ready()
        from tap_plugin.git_serious_double_tap.panels.demo_strip import (
            DemoStripPanelType,
        )

        from tap_web.registry import panel_type_registry

        panel_type_registry.register(DemoStripPanelType.slug, DemoStripPanelType)
