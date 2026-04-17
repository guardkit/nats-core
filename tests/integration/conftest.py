"""Fixtures for integration tests against live NATS on GB10.

Requires:
  - Tailscale VPN connectivity to GB10
  - .env file with RICH_NATS_PASSWORD set
  - NATS server running on GB10 (100.84.90.91:4222)

Fixtures are module-scoped for connection reuse within a test file.
The test stream is created fresh and cleaned up on teardown.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import nats
import nats.aio.client
import nats.js
import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_GB10_NATS_URL = "nats://100.84.90.91:4222"
_NATS_USER = "rich"

_TEST_STREAM_NAME = "PIPELINE_TEST"
_TEST_STREAM_SUBJECTS = ["pipeline.>"]


def _load_password() -> str:
    """Load NATS password from .env file or environment variable."""
    pw = os.environ.get("RICH_NATS_PASSWORD")
    if pw:
        return pw

    # Fall back to .env.integration in project root (avoids NATSConfig .env conflicts)
    project_root = Path(__file__).resolve().parents[2]
    for env_name in (".env.integration", ".env"):
        env_file = project_root / env_name
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                stripped = line.strip()
                if stripped.startswith("RICH_NATS_PASSWORD=") and not stripped.startswith("#"):
                    return stripped.split("=", 1)[1].strip()

    pytest.skip("RICH_NATS_PASSWORD not set (need .env.integration or env var)")
    return ""  # unreachable, but keeps mypy happy


# ---------------------------------------------------------------------------
# Fixtures (module-scoped for connection reuse)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def nats_client() -> nats.aio.client.Client:  # type: ignore[misc]
    """Connect to NATS on GB10, yield the client, disconnect on teardown."""
    password = _load_password()
    nc = await nats.connect(
        _GB10_NATS_URL,
        user=_NATS_USER,
        password=password,
        connect_timeout=10,
        name=f"nats-core-integration-{uuid.uuid4().hex[:8]}",
    )
    yield nc
    await nc.drain()
    await nc.close()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def jetstream(nats_client: nats.aio.client.Client) -> nats.js.JetStreamContext:  # type: ignore[misc]
    """Create a JetStream context from the live client."""
    return nats_client.jetstream()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def test_stream(jetstream: nats.js.JetStreamContext) -> str:  # type: ignore[misc]
    """Ensure a PIPELINE_TEST stream exists, clean up on teardown.

    Returns the stream name.
    """
    js = jetstream
    # Delete if leftover from a previous aborted run
    try:
        await js.delete_stream(_TEST_STREAM_NAME)
    except Exception:
        pass

    # Create the test stream
    await js.add_stream(
        name=_TEST_STREAM_NAME,
        subjects=_TEST_STREAM_SUBJECTS,
        max_age=300,  # 5 minutes retention
    )
    yield _TEST_STREAM_NAME

    # Teardown: clean up the test stream
    try:
        await js.delete_stream(_TEST_STREAM_NAME)
    except Exception:
        pass


def make_test_correlation_id() -> str:
    """Generate a unique correlation ID for test isolation."""
    return f"test-{uuid.uuid4().hex[:12]}"
