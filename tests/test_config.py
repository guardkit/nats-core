"""Tests for nats_core.config — NATSConfig pydantic-settings model."""

from __future__ import annotations

import pytest
from pydantic_settings import BaseSettings

from nats_core.config import NATSConfig

# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.smoke
class TestNATSConfigSmoke:
    """Core happy-path scenarios for NATSConfig."""

    def test_nats_config_is_base_settings_subclass(self) -> None:
        """NATSConfig must inherit from pydantic-settings BaseSettings."""
        assert issubclass(NATSConfig, BaseSettings)

    def test_nats_config_instantiates_with_defaults(self) -> None:
        """NATSConfig can be instantiated without any arguments."""
        cfg = NATSConfig()
        assert isinstance(cfg, NATSConfig)

    def test_nats_config_has_model_config(self) -> None:
        """NATSConfig must define model_config with env_prefix and env_file."""
        mc = NATSConfig.model_config
        assert mc.get("env_prefix") == "NATS_"
        assert mc.get("env_file") == ".env"


# ---------------------------------------------------------------------------
# Key example tests
# ---------------------------------------------------------------------------


@pytest.mark.key_example
class TestNATSConfigExport:
    """NATSConfig is publicly exported from the package."""

    def test_nats_config_importable_from_package(self) -> None:
        """NATSConfig should be importable directly from nats_core."""
        from nats_core import NATSConfig as Imported

        assert Imported is NATSConfig

    def test_nats_config_in_all(self) -> None:
        """NATSConfig must appear in nats_core.__all__."""
        import nats_core

        assert "NATSConfig" in nats_core.__all__


# ---------------------------------------------------------------------------
# Boundary / edge-case tests
# ---------------------------------------------------------------------------


@pytest.mark.boundary
class TestNATSConfigBoundary:
    """Boundary and structural checks."""

    def test_model_config_is_settings_config_dict(self) -> None:
        """model_config should be a SettingsConfigDict (or compatible mapping)."""
        mc = NATSConfig.model_config
        # SettingsConfigDict is a TypedDict at runtime; just verify it's a dict
        assert isinstance(mc, dict)

    def test_module_has_future_annotations(self) -> None:
        """config.py must use `from __future__ import annotations`."""
        import nats_core.config as mod

        assert hasattr(mod, "__annotations__") or True  # import succeeds → future ok
        # More concrete: check the source
        import inspect

        source = inspect.getsource(mod)
        assert "from __future__ import annotations" in source

    def test_module_has_google_style_docstring(self) -> None:
        """config module must have a module-level docstring."""
        import nats_core.config as mod

        assert mod.__doc__ is not None
        assert len(mod.__doc__.strip()) > 0
