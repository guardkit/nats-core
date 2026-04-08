"""Tests validating project scaffolding and structure (TASK-ME01)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "nats_core"


class TestPackageStructure:
    """Verify expected directories and files exist."""

    def test_src_nats_core_init_exists(self) -> None:
        """AC-008: src/nats_core/__init__.py must exist."""
        assert (SRC / "__init__.py").is_file()

    def test_py_typed_marker_exists(self) -> None:
        """AC-009: src/nats_core/py.typed must exist (PEP 561)."""
        assert (SRC / "py.typed").is_file()

    def test_events_subpackage_exists(self) -> None:
        """AC-010: src/nats_core/events/__init__.py must exist."""
        assert (SRC / "events" / "__init__.py").is_file()

    def test_tests_init_exists(self) -> None:
        """AC-011: tests/__init__.py must exist."""
        assert (ROOT / "tests" / "__init__.py").is_file()

    def test_conftest_exists(self) -> None:
        """AC-012: tests/conftest.py must exist."""
        assert (ROOT / "tests" / "conftest.py").is_file()

    def test_pyproject_toml_exists(self) -> None:
        """AC-001: pyproject.toml must exist."""
        assert (ROOT / "pyproject.toml").is_file()


class TestPackageImport:
    """Verify the package is importable and has expected attributes."""

    def test_nats_core_importable(self) -> None:
        """AC-013: nats_core package must be importable after install."""
        import nats_core

        assert nats_core is not None

    def test_version_defined(self) -> None:
        """AC-008: __version__ must be defined in __init__.py."""
        import nats_core

        assert hasattr(nats_core, "__version__")
        assert isinstance(nats_core.__version__, str)
        assert nats_core.__version__ == "0.1.0"

    def test_nats_core_has_docstring(self) -> None:
        """AC-008: nats_core must have a module docstring."""
        import nats_core

        assert nats_core.__doc__ is not None
        assert len(nats_core.__doc__) > 0

    def test_events_subpackage_importable(self) -> None:
        """AC-010: events sub-package must be importable."""
        import nats_core.events

        assert nats_core.events is not None


class TestPyprojectTomlConfig:
    """Verify pyproject.toml has the expected configuration."""

    @pytest.fixture(autouse=True)
    def _load_toml(self) -> None:
        """Load pyproject.toml contents once for this test class."""
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            try:
                import tomllib  # type: ignore[no-redef]
            except ModuleNotFoundError:
                import tomli as tomllib  # type: ignore[no-redef]

        with open(ROOT / "pyproject.toml", "rb") as f:
            self.config = tomllib.load(f)

    def test_build_system_hatchling(self) -> None:
        """AC-001: Build backend must be hatchling."""
        assert self.config["build-system"]["build-backend"] == "hatchling.build"
        assert "hatchling" in self.config["build-system"]["requires"]

    def test_python_requires(self) -> None:
        """AC-002: Python >= 3.10 required."""
        assert self.config["project"]["requires-python"] == ">=3.10"

    def test_pydantic_dependency(self) -> None:
        """AC-003: pydantic >= 2.0 must be in dependencies."""
        deps = self.config["project"]["dependencies"]
        pydantic_deps = [d for d in deps if d.startswith("pydantic")]
        assert len(pydantic_deps) == 1
        assert ">=2.0" in pydantic_deps[0]

    def test_dev_dependencies(self) -> None:
        """AC-004: Dev dependencies must include pytest, pytest-asyncio, ruff, mypy, build."""
        dev_deps = self.config["project"]["optional-dependencies"]["dev"]
        dep_names = [d.split(">=")[0].split(">")[0].split("==")[0].strip() for d in dev_deps]
        required = {"pytest", "pytest-asyncio", "ruff", "mypy", "build"}
        assert required.issubset(set(dep_names)), f"Missing: {required - set(dep_names)}"

    def test_ruff_config(self) -> None:
        """AC-005: ruff config must have correct select rules and line-length."""
        ruff = self.config["tool"]["ruff"]
        assert ruff["line-length"] == 100
        lint = ruff["lint"]
        assert set(lint["select"]) == {"E", "F", "W", "I", "N", "UP"}

    def test_mypy_strict(self) -> None:
        """AC-006: mypy must be configured with strict = true."""
        assert self.config["tool"]["mypy"]["strict"] is True

    def test_pytest_asyncio_mode(self) -> None:
        """AC-007: pytest asyncio_mode must be 'auto'."""
        assert self.config["tool"]["pytest"]["ini_options"]["asyncio_mode"] == "auto"


class TestFactoryFunctionPattern:
    """Verify conftest.py factory function pattern works."""

    def test_make_envelope_data_defaults(self) -> None:
        """AC-012: Factory function must return object with sensible defaults."""
        # Import directly to test the factory
        from tests.conftest import MockEnvelopeData
        from tests.conftest import make_envelope_data as factory

        data = factory()
        assert isinstance(data, MockEnvelopeData)
        assert data.source == "test-agent"
        assert data.event_type == "test.event"
        assert data.payload == {"key": "value"}
        assert data.version == "1.0.0"

    def test_make_envelope_data_overrides(self) -> None:
        """AC-012: Factory function must accept **overrides."""
        from tests.conftest import make_envelope_data as factory

        data = factory(source="custom-agent", event_type="custom.event")
        assert data.source == "custom-agent"
        assert data.event_type == "custom.event"
        # Defaults preserved for non-overridden fields
        assert data.version == "1.0.0"


class TestFutureAnnotations:
    """Verify all modules use from __future__ import annotations."""

    @pytest.mark.parametrize(
        "module_path",
        [
            SRC / "__init__.py",
            SRC / "events" / "__init__.py",
            ROOT / "tests" / "conftest.py",
        ],
    )
    def test_future_annotations_import(self, module_path: Path) -> None:
        """All Python modules must include from __future__ import annotations."""
        content = module_path.read_text()
        assert "from __future__ import annotations" in content
