from pathlib import Path

from apk_hacker.domain.services.hook_search import HookSearch
from apk_hacker.domain.services.method_indexer import JavaMethodIndexer


def test_method_indexer_extracts_class_and_method_signatures() -> None:
    root = Path("tests/fixtures/jadx_sources")

    result = JavaMethodIndexer().build(root)

    class_names = {item.class_name for item in result.classes}
    methods = {(item.class_name, item.method_name) for item in result.methods}

    assert "com.demo.net.Config" in class_names
    assert "com.demo.entry.MainActivity" in class_names
    assert ("com.demo.entry.MainActivity", "onCreate") in methods
    assert ("com.demo.net.Config", "buildUploadUrl") in methods
    assert ("com.demo.net.Config", "buildBackupUrl") in methods
    assert ("com.demo.net.Config", "buildTelemetryPath") in methods
    assert {
        item.class_name: item.source_path
        for item in result.classes
    } == {
        "com.demo.entry.MainActivity": "com/demo/entry/MainActivity.java",
        "com.demo.net.Config": "com/demo/net/Config.java",
    }


def test_method_indexer_tracks_overloads_and_line_hints() -> None:
    root = Path("tests/fixtures/jadx_sources")

    result = JavaMethodIndexer().build(root)

    overloads = [
        item
        for item in result.methods
        if item.class_name == "com.demo.net.Config" and item.method_name == "buildUploadUrl"
    ]

    assert len(overloads) == 2
    assert {item.overload_count for item in overloads} == {2}
    assert all(item.line_hint is not None and item.line_hint > 0 for item in overloads)


def test_hook_search_filters_methods_by_keyword() -> None:
    index = JavaMethodIndexer().build(Path("tests/fixtures/jadx_sources"))

    search = HookSearch()

    upload_matches = search.search(index, "upload")
    activity_matches = search.search(index, "oncreate mainactivity")
    telemetry_matches = search.search(index, "telemetry config")

    assert {(item.class_name, item.method_name) for item in upload_matches} == {
        ("com.demo.net.Config", "buildUploadUrl"),
    }
    assert {(item.class_name, item.method_name) for item in activity_matches} == {
        ("com.demo.entry.MainActivity", "onCreate"),
    }
    assert {(item.class_name, item.method_name) for item in telemetry_matches} == {
        ("com.demo.net.Config", "buildTelemetryPath"),
    }
