"""Tests for TASK-FR-001: Fleet Registration scaffolding.

Validates that all required stub files exist, contain the mandatory
``from __future__ import annotations`` import, and that the package
remains importable.
"""

from __future__ import annotations

import ast
import importlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "nats_core"

# ---------------------------------------------------------------------------
# AC-001: src/nats_core/manifest.py exists (stub with future annotations)
# ---------------------------------------------------------------------------


class TestManifestFileExists:
    """AC-001: manifest.py must exist and have the future annotations import."""

    @pytest.mark.unit
    def test_manifest_py_exists(self) -> None:
        """manifest.py must exist in the nats_core package."""
        assert (SRC / "manifest.py").is_file(), "src/nats_core/manifest.py does not exist"

    @pytest.mark.unit
    def test_manifest_py_has_future_annotations(self) -> None:
        """manifest.py must include from __future__ import annotations."""
        content = (SRC / "manifest.py").read_text()
        assert "from __future__ import annotations" in content

    @pytest.mark.unit
    def test_manifest_py_is_valid_python(self) -> None:
        """manifest.py must parse as valid Python."""
        content = (SRC / "manifest.py").read_text()
        ast.parse(content, filename="manifest.py")


# ---------------------------------------------------------------------------
# AC-002: src/nats_core/_routing.py exists (stub with future annotations)
# ---------------------------------------------------------------------------


class TestRoutingFileExists:
    """AC-002: _routing.py must exist and have the future annotations import."""

    @pytest.mark.unit
    def test_routing_py_exists(self) -> None:
        """_routing.py must exist in the nats_core package."""
        assert (SRC / "_routing.py").is_file(), "src/nats_core/_routing.py does not exist"

    @pytest.mark.unit
    def test_routing_py_has_future_annotations(self) -> None:
        """_routing.py must include from __future__ import annotations."""
        content = (SRC / "_routing.py").read_text()
        assert "from __future__ import annotations" in content

    @pytest.mark.unit
    def test_routing_py_is_valid_python(self) -> None:
        """_routing.py must parse as valid Python."""
        content = (SRC / "_routing.py").read_text()
        ast.parse(content, filename="_routing.py")

    @pytest.mark.unit
    def test_routing_py_is_stub_only(self) -> None:
        """_routing.py must be a stub — no class/function definitions yet."""
        content = (SRC / "_routing.py").read_text()
        tree = ast.parse(content, filename="_routing.py")
        for node in ast.walk(tree):
            assert not isinstance(
                node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ), "_routing.py should be a stub with no logic"


# ---------------------------------------------------------------------------
# AC-003: src/nats_core/events/fleet.py exists (stub with future annotations)
# ---------------------------------------------------------------------------


class TestEventsFleetFileExists:
    """AC-003: events/fleet.py must exist and have the future annotations import."""

    @pytest.mark.unit
    def test_events_fleet_py_exists(self) -> None:
        """events/fleet.py must exist in the nats_core/events package."""
        assert (
            SRC / "events" / "fleet.py"
        ).is_file(), "src/nats_core/events/fleet.py does not exist"

    @pytest.mark.unit
    def test_events_fleet_py_has_future_annotations(self) -> None:
        """events/fleet.py must include from __future__ import annotations."""
        content = (SRC / "events" / "fleet.py").read_text()
        assert "from __future__ import annotations" in content

    @pytest.mark.unit
    def test_events_fleet_py_is_valid_python(self) -> None:
        """events/fleet.py must parse as valid Python."""
        content = (SRC / "events" / "fleet.py").read_text()
        ast.parse(content, filename="fleet.py")

    @pytest.mark.unit
    def test_events_fleet_py_is_stub_only(self) -> None:
        """events/fleet.py must be a stub — no class/function definitions yet."""
        content = (SRC / "events" / "fleet.py").read_text()
        tree = ast.parse(content, filename="fleet.py")
        for node in ast.walk(tree):
            assert not isinstance(
                node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ), "events/fleet.py should be a stub with no logic"


# ---------------------------------------------------------------------------
# AC-004: src/nats_core/py.typed exists (empty file — PEP 561)
# ---------------------------------------------------------------------------


class TestPyTypedExists:
    """AC-004: py.typed must exist as an empty marker file."""

    @pytest.mark.unit
    def test_py_typed_exists(self) -> None:
        """py.typed must exist in the nats_core package."""
        assert (SRC / "py.typed").is_file(), "src/nats_core/py.typed does not exist"

    @pytest.mark.unit
    def test_py_typed_is_empty(self) -> None:
        """py.typed must be an empty file per PEP 561."""
        content = (SRC / "py.typed").read_text()
        assert content.strip() == "", "py.typed should be empty"


# ---------------------------------------------------------------------------
# AC-005: python -c "import nats_core" succeeds without error
# ---------------------------------------------------------------------------


class TestPackageImportable:
    """AC-005: The nats_core package must be importable without error."""

    @pytest.mark.unit
    def test_import_nats_core_succeeds(self) -> None:
        """Importing nats_core must not raise."""
        import nats_core

        assert nats_core is not None

    @pytest.mark.unit
    def test_import_nats_core_subprocess(self) -> None:
        """python -c 'import nats_core' must exit 0."""
        result = subprocess.run(
            [sys.executable, "-c", "import nats_core"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Import failed: {result.stderr}"

    @pytest.mark.unit
    def test_import_routing_module(self) -> None:
        """The _routing stub module must be importable."""
        mod = importlib.import_module("nats_core._routing")
        assert mod is not None

    @pytest.mark.unit
    def test_import_events_fleet_module(self) -> None:
        """The events.fleet stub module must be importable."""
        mod = importlib.import_module("nats_core.events.fleet")
        assert mod is not None


# ---------------------------------------------------------------------------
# AC-006: All stub files include from __future__ import annotations as first import
# ---------------------------------------------------------------------------


class TestFutureAnnotationsFirstImport:
    """AC-006: All stub files must have future annotations as the first import."""

    STUB_FILES = [
        SRC / "manifest.py",
        SRC / "_routing.py",
        SRC / "events" / "fleet.py",
    ]

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "stub_path",
        [
            SRC / "manifest.py",
            SRC / "_routing.py",
            SRC / "events" / "fleet.py",
        ],
        ids=["manifest.py", "_routing.py", "events/fleet.py"],
    )
    def test_future_annotations_present(self, stub_path: Path) -> None:
        """Each stub file must contain from __future__ import annotations."""
        content = stub_path.read_text()
        assert "from __future__ import annotations" in content, (
            f"{stub_path.name} missing 'from __future__ import annotations'"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "stub_path",
        [
            SRC / "manifest.py",
            SRC / "_routing.py",
            SRC / "events" / "fleet.py",
        ],
        ids=["manifest.py", "_routing.py", "events/fleet.py"],
    )
    def test_future_annotations_is_first_import(self, stub_path: Path) -> None:
        """from __future__ import annotations must be the first import statement."""
        tree = ast.parse(stub_path.read_text(), filename=stub_path.name)
        imports = [
            node
            for node in ast.iter_child_nodes(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        assert len(imports) > 0, f"No imports found in {stub_path.name}"
        first_import = imports[0]
        assert isinstance(first_import, ast.ImportFrom), (
            f"First import in {stub_path.name} is not an ImportFrom"
        )
        assert first_import.module == "__future__", (
            f"First import in {stub_path.name} is not from __future__"
        )


# ---------------------------------------------------------------------------
# AC-007: No logic implemented in this task — stubs only
# ---------------------------------------------------------------------------


class TestNewFilesAreStubsOnly:
    """AC-007: Newly created files must be stubs with no logic."""

    @pytest.mark.unit
    def test_routing_has_no_definitions(self) -> None:
        """_routing.py must contain no class or function definitions."""
        content = (SRC / "_routing.py").read_text()
        tree = ast.parse(content, filename="_routing.py")
        definitions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert definitions == [], (
            "_routing.py should be a stub with no definitions"
        )

    @pytest.mark.unit
    def test_events_fleet_has_no_definitions(self) -> None:
        """events/fleet.py must contain no class or function definitions."""
        content = (SRC / "events" / "fleet.py").read_text()
        tree = ast.parse(content, filename="fleet.py")
        definitions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        assert definitions == [], (
            "events/fleet.py should be a stub with no definitions"
        )
