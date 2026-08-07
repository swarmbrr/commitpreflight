"""Pre-flight lint for commit messages written by AI coding agents."""

from commitpreflight.rules import Config, Finding, check

__all__ = ["Config", "Finding", "__version__", "check"]
__version__ = "0.1.1"
