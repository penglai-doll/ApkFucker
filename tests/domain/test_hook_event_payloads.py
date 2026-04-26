from apk_hacker.domain.models.hook_event import HookEvent


def test_hook_event_round_trips_through_payload() -> None:
    event = HookEvent(
        timestamp="2026-04-26T12:00:00Z",
        job_id="job-001",
        event_type="method_return",
        source="frida",
        class_name="com.example.NetClient",
        method_name="submit",
        arguments=("imei", "token"),
        return_value="ok",
        stacktrace="com.example.NetClient.submit:42",
        raw_payload={"session_id": "session-001", "hook_type": "method"},
    )

    payload = event.to_payload()
    assert payload == {
        "timestamp": "2026-04-26T12:00:00Z",
        "job_id": "job-001",
        "event_type": "method_return",
        "source": "frida",
        "class_name": "com.example.NetClient",
        "method_name": "submit",
        "arguments": ["imei", "token"],
        "return_value": "ok",
        "stacktrace": "com.example.NetClient.submit:42",
        "raw_payload": {"session_id": "session-001", "hook_type": "method"},
    }
    assert HookEvent.from_payload(payload) == event


def test_hook_event_from_payload_rejects_invalid_payload() -> None:
    assert HookEvent.from_payload(None) is None
    assert HookEvent.from_payload({"job_id": "missing-required-fields"}) is None
