"""Build-time local VAD/turn-detector assets; no credentials or learner content."""

from livekit.agents import Plugin
from livekit.plugins import silero  # noqa: F401
from livekit.plugins.turn_detector import multilingual  # noqa: F401

if __name__ == "__main__":
    for plugin in Plugin.registered_plugins:
        # The pinned SDK initializes both registered local detector runners.
        plugin.download_files()
