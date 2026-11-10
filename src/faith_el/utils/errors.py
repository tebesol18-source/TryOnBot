"""Error types for Faith-EL configuration loading and validation.

Every message produced here is SAFE TO LOG: it never contains secret values
(tokens, photo data). Only key names and expected formats are mentioned.
"""
from __future__ import annotations


class ConfigError(Exception):
    """Base class for all configuration errors."""


class ConfigFileError(ConfigError):
    """A config file is missing, unreadable or not valid YAML."""


class ConfigValidationError(ConfigError):
    """A config value is missing, has the wrong type or an illegal value."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = list(problems)
        super().__init__("Configuration validation failed:\n- " + "\n- ".join(self.problems))


class SecretNotConfiguredError(ConfigError):
    """The bot token is absent from the environment.

    The message intentionally mentions only the ENV VAR NAME, never a value.
    """

    def __init__(self, env_var: str) -> None:
        super().__init__(
            f"Required environment variable {env_var!r} is not set. "
            "(Value withheld on purpose — secrets are never shown.)"
        )
