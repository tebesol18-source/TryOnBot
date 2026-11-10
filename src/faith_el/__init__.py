"""Faith-EL Virtual Stylist — application package.

Sprint 2: configuration loader & validation API.

    load_configuration, get_bot_token, require_bot_token
    AppConfiguration + config dataclasses
    ConfigError / ConfigFileError / ConfigValidationError / SecretNotConfiguredError
"""
from .config_loader import get_bot_token, load_configuration, require_bot_token
from .config_models import (
    AdminsConfig,
    AppConfig,
    AppConfiguration,
    Boutique,
    BoutiqueConfig,
    CatalogConfig,
    ChannelConfig,
    ConsentScope,
    ImageGenConfig,
    LoggingConfig,
    PolicyConfig,
    PrivacyConfig,
    RetentionConfig,
    Settings,
    StorageConfig,
    TelegramConfig,
)
from .utils.errors import (
    ConfigError,
    ConfigFileError,
    ConfigValidationError,
    SecretNotConfiguredError,
)

__all__ = [
    "load_configuration",
    "get_bot_token",
    "require_bot_token",
    "AppConfiguration",
    "Settings",
    "Boutique",
    "BoutiqueConfig",
    "ChannelConfig",
    "AdminsConfig",
    "CatalogConfig",
    "AppConfig",
    "TelegramConfig",
    "StorageConfig",
    "ImageGenConfig",
    "PrivacyConfig",
    "ConsentScope",
    "RetentionConfig",
    "PolicyConfig",
    "LoggingConfig",
    "ConfigError",
    "ConfigFileError",
    "ConfigValidationError",
    "SecretNotConfiguredError",
]
