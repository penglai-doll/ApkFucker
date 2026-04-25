from pathlib import Path

from apk_hacker.domain.models.hook_event import HookEvent
from apk_hacker.infrastructure.persistence.hook_log_store import HookLogStore


def test_hook_log_store_inserts_and_reads_events(tmp_path: Path) -> None:
    store = HookLogStore(tmp_path / "hooks.sqlite3")
    event = HookEvent(
        timestamp="2026-04-05T00:00:00Z",
        job_id="job-1",
        event_type="method_call",
        source="fake",
        class_name="com.demo.net.Config",
        method_name="buildUploadUrl",
        arguments=["demo-c2.example"],
        return_value="https://demo-c2.example/api/upload",
        stacktrace="demo stack",
        raw_payload={"ok": True},
    )

    store.insert(event)
    rows = store.list_for_job("job-1")

    assert len(rows) == 1
    assert rows[0].event_type == "method_call"
    assert rows[0].arguments == ("demo-c2.example",)


def test_hook_log_store_filters_by_job_and_orders_by_timestamp(tmp_path: Path) -> None:
    store = HookLogStore(tmp_path / "hooks.sqlite3")

    store.insert(
        HookEvent(
            timestamp="2026-04-05T00:00:01Z",
            job_id="job-1",
            event_type="method_call",
            source="fake",
            class_name="com.demo.net.Config",
            method_name="lateCall",
            arguments=[],
            return_value=None,
            stacktrace="late stack",
            raw_payload={"seq": 2},
        )
    )
    store.insert(
        HookEvent(
            timestamp="2026-04-05T00:00:00Z",
            job_id="job-1",
            event_type="method_call",
            source="fake",
            class_name="com.demo.net.Config",
            method_name="earlyCall",
            arguments=[],
            return_value=None,
            stacktrace="early stack",
            raw_payload={"seq": 1},
        )
    )
    store.insert(
        HookEvent(
            timestamp="2026-04-05T00:00:02Z",
            job_id="job-2",
            event_type="method_call",
            source="fake",
            class_name="com.demo.net.Config",
            method_name="otherJob",
            arguments=[],
            return_value=None,
            stacktrace="other stack",
            raw_payload={"seq": 3},
        )
    )

    rows = store.list_for_job("job-1")

    assert [row.method_name for row in rows] == ["earlyCall", "lateCall"]


def test_hook_log_store_exposes_normalized_dynamic_events(tmp_path: Path) -> None:
    store = HookLogStore(tmp_path / "hooks.sqlite3")
    store.insert(
        HookEvent(
            timestamp="2026-04-05T00:00:00Z",
            job_id="job-1",
            event_type="crypto_call",
            source="real",
            class_name="javax.crypto.Cipher",
            method_name="doFinal",
            arguments=["plaintext"],
            return_value="ciphertext",
            stacktrace="",
            raw_payload={
                "event_type": "crypto_call",
                "hook_type": "crypto",
                "session_id": "session-1",
                "source_script": "01_cipher.js",
            },
        )
    )

    rows = store.list_dynamic_for_job("job-1")

    assert len(rows) == 1
    assert rows[0].hook_type == "crypto"
    assert rows[0].session_id == "session-1"
    assert rows[0].source_script == "01_cipher.js"
    assert rows[0].arguments == ("plaintext",)
