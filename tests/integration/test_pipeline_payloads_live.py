"""Integration tests for v2.2 pipeline payloads against live NATS on GB10.

Proves the new payloads round-trip cleanly through a real JetStream instance:
envelope serialisation → stream persistence → consumer pull → deserialisation.

Requires:
  - Live NATS on GB10 via Tailscale (100.84.90.91:4222)
  - RICH_NATS_PASSWORD set (via .env or env var)
  - pytest -m integration to run

TASK-NCFA-002.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import nats.aio.client
import nats.js
import pytest
from pydantic import ValidationError

from nats_core.envelope import EventType, MessageEnvelope
from nats_core.events import (
    BuildPausedPayload,
    BuildQueuedPayload,
    BuildResumedPayload,
    StageCompletePayload,
    StageGatedPayload,
)
from nats_core.topics import Topics

from .conftest import make_test_correlation_id

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="module")]

_NOW = datetime(2026, 4, 15, 16, 30, 12, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def _make_envelope(
    payload: dict[str, Any],
    event_type: EventType,
    correlation_id: str | None = None,
) -> MessageEnvelope:
    return MessageEnvelope(
        message_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        version="1.0",
        source_id="integration-test",
        event_type=event_type,
        correlation_id=correlation_id,
        payload=payload,
    )


def _make_build_queued_data(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-TEST001",
        "repo": "guardkit/lpa-platform",
        "branch": "main",
        "feature_yaml_path": "specs/FEAT-TEST001.yaml",
        "max_turns": 5,
        "sdk_timeout_seconds": 1800,
        "wave_gating": False,
        "config_overrides": None,
        "triggered_by": "cli",
        "originating_adapter": "terminal",
        "originating_user": "test-runner",
        "correlation_id": make_test_correlation_id(),
        "parent_request_id": None,
        "retry_count": 0,
        "requested_at": _NOW.isoformat(),
        "queued_at": _NOW.isoformat(),
    }
    defaults.update(overrides)
    return defaults


def _make_build_paused_data(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-TEST001",
        "build_id": "build-FEAT-TEST001-20260415163012",
        "stage_label": "autobuild",
        "gate_mode": "FLAG_FOR_REVIEW",
        "coach_score": 0.65,
        "rationale": "Coach score below threshold",
        "approval_subject": "agents.approval.forge.FEAT-TEST001",
        "paused_at": _NOW.isoformat(),
        "correlation_id": make_test_correlation_id(),
    }
    defaults.update(overrides)
    return defaults


def _make_build_resumed_data(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-TEST001",
        "build_id": "build-FEAT-TEST001-20260415163012",
        "stage_label": "autobuild",
        "decision": "approve",
        "responder": "rich",
        "resumed_at": _NOW.isoformat(),
        "correlation_id": make_test_correlation_id(),
    }
    defaults.update(overrides)
    return defaults


def _make_stage_complete_data(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-TEST001",
        "build_id": "build-FEAT-TEST001-20260415163012",
        "stage_label": "autobuild",
        "target_kind": "subagent",
        "target_identifier": "autobuild-player-coach",
        "status": "PASSED",
        "gate_mode": None,
        "coach_score": 0.92,
        "duration_secs": 42.5,
        "completed_at": _NOW.isoformat(),
        "correlation_id": make_test_correlation_id(),
    }
    defaults.update(overrides)
    return defaults


def _make_stage_gated_data(**overrides: Any) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-TEST001",
        "build_id": "build-FEAT-TEST001-20260415163012",
        "stage": "autobuild",
        "gate_mode": "hard_stop",
        "coach_score": 0.55,
        "threshold": 0.75,
        "details": "Hard stop: score below threshold",
        "correlation_id": make_test_correlation_id(),
        "gated_at": _NOW.isoformat(),
    }
    defaults.update(overrides)
    return defaults


async def _publish_and_pull(
    jetstream: nats.js.JetStreamContext,
    test_stream: str,
    subject: str,
    envelope: MessageEnvelope,
) -> MessageEnvelope:
    """Publish an envelope to a subject and pull it back from the stream."""
    data = envelope.model_dump_json().encode()
    await jetstream.publish(subject, data)

    # Create an ephemeral pull consumer
    consumer_name = f"test-consumer-{uuid.uuid4().hex[:8]}"
    sub = await jetstream.pull_subscribe(
        subject,
        durable=consumer_name,
        stream=test_stream,
    )

    msgs = await sub.fetch(1, timeout=5)
    assert len(msgs) == 1, f"Expected 1 message, got {len(msgs)}"
    msg = msgs[0]
    await msg.ack()

    received = MessageEnvelope.model_validate_json(msg.data)

    # Clean up consumer
    await jetstream.delete_consumer(test_stream, consumer_name)

    return received


# ===================================================================
# 1. Round-trip tests per payload
# ===================================================================


class TestRoundTrip:
    """Each new payload round-trips through live JetStream."""

    async def test_build_queued_round_trip_via_jetstream(
        self, jetstream: nats.js.JetStreamContext, test_stream: str
    ) -> None:
        """Publish BuildQueuedPayload in envelope, consume, deserialise, assert field equality."""
        corr_id = make_test_correlation_id()
        fid = f"FEAT-BQ{uuid.uuid4().hex[:5].upper()}"
        payload_data = _make_build_queued_data(feature_id=fid, correlation_id=corr_id)
        envelope = _make_envelope(payload_data, EventType.BUILD_QUEUED, correlation_id=corr_id)

        subject = Topics.resolve(Topics.Pipeline.BUILD_QUEUED, feature_id=fid)
        received = await _publish_and_pull(jetstream, test_stream, subject, envelope)

        assert received.event_type == EventType.BUILD_QUEUED
        assert received.correlation_id == corr_id

        parsed = BuildQueuedPayload.model_validate(received.payload)
        assert parsed.feature_id == fid
        assert parsed.repo == "guardkit/lpa-platform"
        assert parsed.correlation_id == corr_id
        assert parsed.triggered_by == "cli"

    async def test_build_paused_round_trip(
        self, jetstream: nats.js.JetStreamContext, test_stream: str
    ) -> None:
        """BuildPausedPayload round-trips through JetStream."""
        corr_id = make_test_correlation_id()
        fid = f"FEAT-BP{uuid.uuid4().hex[:5].upper()}"
        payload_data = _make_build_paused_data(feature_id=fid, correlation_id=corr_id)
        envelope = _make_envelope(payload_data, EventType.BUILD_PAUSED, correlation_id=corr_id)

        subject = Topics.resolve(Topics.Pipeline.BUILD_PAUSED, feature_id=fid)
        received = await _publish_and_pull(jetstream, test_stream, subject, envelope)

        parsed = BuildPausedPayload.model_validate(received.payload)
        assert parsed.gate_mode == "FLAG_FOR_REVIEW"
        assert parsed.correlation_id == corr_id

    async def test_build_resumed_round_trip(
        self, jetstream: nats.js.JetStreamContext, test_stream: str
    ) -> None:
        """BuildResumedPayload round-trips through JetStream."""
        corr_id = make_test_correlation_id()
        fid = f"FEAT-BR{uuid.uuid4().hex[:5].upper()}"
        payload_data = _make_build_resumed_data(feature_id=fid, correlation_id=corr_id)
        envelope = _make_envelope(payload_data, EventType.BUILD_RESUMED, correlation_id=corr_id)

        subject = Topics.resolve(Topics.Pipeline.BUILD_RESUMED, feature_id=fid)
        received = await _publish_and_pull(jetstream, test_stream, subject, envelope)

        parsed = BuildResumedPayload.model_validate(received.payload)
        assert parsed.decision == "approve"
        assert parsed.responder == "rich"

    async def test_stage_complete_round_trip(
        self, jetstream: nats.js.JetStreamContext, test_stream: str
    ) -> None:
        """StageCompletePayload round-trips through JetStream."""
        corr_id = make_test_correlation_id()
        fid = f"FEAT-SC{uuid.uuid4().hex[:5].upper()}"
        payload_data = _make_stage_complete_data(feature_id=fid, correlation_id=corr_id)
        envelope = _make_envelope(
            payload_data, EventType.STAGE_COMPLETE, correlation_id=corr_id
        )

        subject = Topics.resolve(Topics.Pipeline.STAGE_COMPLETE, feature_id=fid)
        received = await _publish_and_pull(jetstream, test_stream, subject, envelope)

        parsed = StageCompletePayload.model_validate(received.payload)
        assert parsed.status == "PASSED"
        assert parsed.target_kind == "subagent"
        assert parsed.coach_score == pytest.approx(0.92)

    async def test_stage_gated_round_trip(
        self, jetstream: nats.js.JetStreamContext, test_stream: str
    ) -> None:
        """StageGatedPayload round-trips through JetStream."""
        corr_id = make_test_correlation_id()
        fid = f"FEAT-SG{uuid.uuid4().hex[:5].upper()}"
        payload_data = _make_stage_gated_data(feature_id=fid, correlation_id=corr_id)
        envelope = _make_envelope(payload_data, EventType.STAGE_GATED, correlation_id=corr_id)

        subject = Topics.resolve(Topics.Pipeline.STAGE_GATED, feature_id=fid)
        received = await _publish_and_pull(jetstream, test_stream, subject, envelope)

        parsed = StageGatedPayload.model_validate(received.payload)
        assert parsed.gate_mode == "hard_stop"
        assert parsed.coach_score == pytest.approx(0.55)


# ===================================================================
# 2. AckWait crash-recovery test
# ===================================================================


class TestAckWaitRedelivery:
    """Prove JetStream's AckWait redelivery mechanism."""

    async def test_build_queued_unacked_redelivery(
        self, jetstream: nats.js.JetStreamContext, test_stream: str
    ) -> None:
        """Publish, pull without ack, wait for AckWait, pull again — same message redelivered."""
        corr_id = make_test_correlation_id()
        payload_data = _make_build_queued_data(correlation_id=corr_id)
        envelope = _make_envelope(payload_data, EventType.BUILD_QUEUED, correlation_id=corr_id)

        subject = Topics.resolve(
            Topics.Pipeline.BUILD_QUEUED, feature_id="FEAT-REDELIVER"
        )
        await jetstream.publish(subject, envelope.model_dump_json().encode())

        # Create consumer with short AckWait (3 seconds) for test speed
        consumer_name = f"redelivery-test-{uuid.uuid4().hex[:8]}"
        config = nats.js.api.ConsumerConfig(
            durable_name=consumer_name,
            ack_wait=3,  # 3 seconds
            filter_subject=subject,
        )
        await jetstream.add_consumer(test_stream, config)
        sub = await jetstream.pull_subscribe_bind(consumer_name, test_stream)

        # First pull — do NOT ack
        msgs = await sub.fetch(1, timeout=5)
        assert len(msgs) == 1
        first_data = json.loads(msgs[0].data)
        first_msg_id = first_data["message_id"]
        # Intentionally not calling msgs[0].ack()

        # Wait for AckWait to expire (3s + 1s buffer)
        await asyncio.sleep(4)

        # Second pull — same message should be redelivered
        msgs2 = await sub.fetch(1, timeout=5)
        assert len(msgs2) == 1
        second_data = json.loads(msgs2[0].data)
        second_msg_id = second_data["message_id"]

        # Same message redelivered
        assert first_msg_id == second_msg_id
        assert second_data["correlation_id"] == corr_id

        # Ack to clean up
        await msgs2[0].ack()

        # Clean up consumer
        await jetstream.delete_consumer(test_stream, consumer_name)


# ===================================================================
# 3. Correlation ID threading test
# ===================================================================


class TestCorrelationIdThreading:
    """Verify correlation_id threads through a sequence of build events."""

    async def test_correlation_id_threads_through_build_events(
        self, jetstream: nats.js.JetStreamContext, test_stream: str
    ) -> None:
        """Publish 5 events with same correlation_id, subscribe, verify all arrive."""
        corr_id = make_test_correlation_id()
        feature_id = "FEAT-CORR001"

        # Build the sequence of events
        events: list[tuple[str, EventType, dict[str, Any]]] = [
            (
                Topics.resolve(Topics.Pipeline.BUILD_QUEUED, feature_id=feature_id),
                EventType.BUILD_QUEUED,
                _make_build_queued_data(
                    feature_id=feature_id, correlation_id=corr_id
                ),
            ),
            (
                Topics.resolve(Topics.Pipeline.BUILD_STARTED, feature_id=feature_id),
                EventType.BUILD_STARTED,
                {
                    "feature_id": feature_id,
                    "build_id": f"build-{feature_id}-20260415163012",
                    "wave_total": 2,
                },
            ),
            (
                Topics.resolve(Topics.Pipeline.BUILD_PROGRESS, feature_id=feature_id),
                EventType.BUILD_PROGRESS,
                {
                    "feature_id": feature_id,
                    "build_id": f"build-{feature_id}-20260415163012",
                    "wave": 1,
                    "wave_total": 2,
                    "overall_progress_pct": 50.0,
                    "elapsed_seconds": 60,
                },
            ),
            (
                Topics.resolve(
                    Topics.Pipeline.STAGE_COMPLETE, feature_id=feature_id
                ),
                EventType.STAGE_COMPLETE,
                _make_stage_complete_data(
                    feature_id=feature_id, correlation_id=corr_id
                ),
            ),
            (
                Topics.resolve(
                    Topics.Pipeline.BUILD_COMPLETE, feature_id=feature_id
                ),
                EventType.BUILD_COMPLETE,
                {
                    "feature_id": feature_id,
                    "build_id": f"build-{feature_id}-20260415163012",
                    "tasks_completed": 3,
                    "tasks_failed": 0,
                    "tasks_total": 3,
                    "duration_seconds": 120,
                    "summary": "All tasks completed",
                },
            ),
        ]

        # Create a consumer on pipeline.> for this feature
        consumer_name = f"corr-test-{uuid.uuid4().hex[:8]}"
        sub = await jetstream.pull_subscribe(
            f"pipeline.*.{feature_id}",
            durable=consumer_name,
            stream=test_stream,
        )

        # Publish all events with same correlation_id
        for subject, event_type, payload_data in events:
            envelope = _make_envelope(payload_data, event_type, correlation_id=corr_id)
            await jetstream.publish(subject, envelope.model_dump_json().encode())

        # Pull all 5 messages
        msgs = await sub.fetch(5, timeout=10)
        assert len(msgs) == 5  # noqa: PLR2004

        # Verify all have the same correlation_id
        received_types = []
        for msg in msgs:
            env = MessageEnvelope.model_validate_json(msg.data)
            assert env.correlation_id == corr_id
            received_types.append(env.event_type)
            await msg.ack()

        # Verify the event type sequence
        expected_types = [
            EventType.BUILD_QUEUED,
            EventType.BUILD_STARTED,
            EventType.BUILD_PROGRESS,
            EventType.STAGE_COMPLETE,
            EventType.BUILD_COMPLETE,
        ]
        assert received_types == expected_types

        # Clean up
        await jetstream.delete_consumer(test_stream, consumer_name)


# ===================================================================
# 4. Forward-compat test
# ===================================================================


class TestForwardCompat:
    """Validate ConfigDict(extra='allow') works over the wire."""

    async def test_build_queued_accepts_unknown_fields_from_future_publisher(
        self, jetstream: nats.js.JetStreamContext, test_stream: str
    ) -> None:
        """Payload with extra field deserialises without error, known fields intact."""
        corr_id = make_test_correlation_id()
        feature_id = f"FEAT-FWD{uuid.uuid4().hex[:4].upper()}"
        payload_data = _make_build_queued_data(
            feature_id=feature_id, correlation_id=corr_id
        )
        # Add a field that current code doesn't know about
        payload_data["session_context"] = {"session_id": "jarvis-voice-001", "adapter": "reachy"}

        envelope = _make_envelope(payload_data, EventType.BUILD_QUEUED, correlation_id=corr_id)
        subject = Topics.resolve(Topics.Pipeline.BUILD_QUEUED, feature_id=feature_id)

        received = await _publish_and_pull(jetstream, test_stream, subject, envelope)

        # Deserialise with current model — should NOT raise
        parsed = BuildQueuedPayload.model_validate(received.payload)
        assert parsed.feature_id == feature_id
        assert parsed.correlation_id == corr_id
        # The extra field is preserved due to extra='allow'
        assert parsed.session_context == {  # type: ignore[attr-defined]
            "session_id": "jarvis-voice-001",
            "adapter": "reachy",
        }


# ===================================================================
# 5. Schema validation rejection test
# ===================================================================


class TestSchemaValidationRejection:
    """Verify invalid payloads fail cleanly on the consumer side."""

    async def test_build_queued_rejects_invalid_feature_id_over_nats(
        self, jetstream: nats.js.JetStreamContext, test_stream: str
    ) -> None:
        """Publish payload with invalid feature_id; consumer-side Pydantic raises."""
        # Manually construct an invalid payload (bypassing Pydantic validation)
        invalid_payload = {
            "feature_id": "bogus",  # Invalid — doesn't match FEAT-XXX
            "repo": "guardkit/lpa-platform",
            "branch": "main",
            "feature_yaml_path": "specs/bogus.yaml",
            "triggered_by": "cli",
            "originating_adapter": "terminal",
            "correlation_id": make_test_correlation_id(),
            "requested_at": _NOW.isoformat(),
            "queued_at": _NOW.isoformat(),
        }
        topic_feature_id = f"FEAT-INV{uuid.uuid4().hex[:5].upper()}"
        envelope = _make_envelope(invalid_payload, EventType.BUILD_QUEUED)
        subject = Topics.resolve(Topics.Pipeline.BUILD_QUEUED, feature_id=topic_feature_id)

        received = await _publish_and_pull(jetstream, test_stream, subject, envelope)

        # Deserialising should raise ValidationError
        with pytest.raises(ValidationError, match="feature_id"):
            BuildQueuedPayload.model_validate(received.payload)


# ===================================================================
# 6. Topic subscription pattern test
# ===================================================================


class TestWildcardSubscription:
    """Verify pipeline.*.{feature_id} wildcard subscription catches all events."""

    async def test_subscribe_all_pipeline_build_events_wildcard(
        self, jetstream: nats.js.JetStreamContext, test_stream: str
    ) -> None:
        """Subscribe to pipeline.*.{feature_id}, publish build events, assert all arrive."""
        feature_id = f"FEAT-WC{uuid.uuid4().hex[:5].upper()}"
        corr_id = make_test_correlation_id()

        # Publish first, then create consumer — avoids deliver_policy timing issues
        build_events: list[tuple[str, EventType, dict[str, Any]]] = [
            (
                Topics.resolve(Topics.Pipeline.BUILD_QUEUED, feature_id=feature_id),
                EventType.BUILD_QUEUED,
                _make_build_queued_data(
                    feature_id=feature_id, correlation_id=corr_id
                ),
            ),
            (
                Topics.resolve(Topics.Pipeline.BUILD_STARTED, feature_id=feature_id),
                EventType.BUILD_STARTED,
                {
                    "feature_id": feature_id,
                    "build_id": f"build-{feature_id}-20260415163012",
                    "wave_total": 1,
                },
            ),
            (
                Topics.resolve(Topics.Pipeline.BUILD_PAUSED, feature_id=feature_id),
                EventType.BUILD_PAUSED,
                _make_build_paused_data(
                    feature_id=feature_id, correlation_id=corr_id
                ),
            ),
            (
                Topics.resolve(Topics.Pipeline.BUILD_RESUMED, feature_id=feature_id),
                EventType.BUILD_RESUMED,
                _make_build_resumed_data(
                    feature_id=feature_id, correlation_id=corr_id
                ),
            ),
            (
                Topics.resolve(
                    Topics.Pipeline.BUILD_COMPLETE, feature_id=feature_id
                ),
                EventType.BUILD_COMPLETE,
                {
                    "feature_id": feature_id,
                    "build_id": f"build-{feature_id}-20260415163012",
                    "tasks_completed": 1,
                    "tasks_failed": 0,
                    "tasks_total": 1,
                    "duration_seconds": 30,
                    "summary": "Done",
                },
            ),
        ]

        for subject, event_type, payload_data in build_events:
            envelope = _make_envelope(payload_data, event_type, correlation_id=corr_id)
            await jetstream.publish(subject, envelope.model_dump_json().encode())

        # Create consumer AFTER publishing — use pipeline.> filter and verify
        # that the wildcard catches all build-* subjects for this feature
        consumer_name = f"wildcard-test-{uuid.uuid4().hex[:8]}"
        sub = await jetstream.pull_subscribe(
            f"pipeline.*.{feature_id}",
            durable=consumer_name,
            stream=test_stream,
        )

        # Pull all messages
        msgs = await sub.fetch(5, timeout=10)
        assert len(msgs) == 5  # noqa: PLR2004

        received_types = set()
        for msg in msgs:
            env = MessageEnvelope.model_validate_json(msg.data)
            received_types.add(env.event_type)
            await msg.ack()

        # All 5 build event types should be present
        expected_types = {
            EventType.BUILD_QUEUED,
            EventType.BUILD_STARTED,
            EventType.BUILD_PAUSED,
            EventType.BUILD_RESUMED,
            EventType.BUILD_COMPLETE,
        }
        assert received_types == expected_types

        # Clean up
        await jetstream.delete_consumer(test_stream, consumer_name)
