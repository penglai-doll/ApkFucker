from pathlib import Path

from apk_hacker.domain.services.hook_search import HookSearch
from apk_hacker.domain.services.method_indexer import JavaMethodIndexer


def test_method_indexer_extracts_class_and_method_signatures() -> None:
    root = Path("tests/fixtures/jadx_sources")
    result = JavaMethodIndexer().build(root)

    class_names = {item.class_name for item in result.classes}
    methods = {(item.class_name, item.method_name) for item in result.methods}

    assert "com.demo.net.Config" in class_names
    assert ("com.demo.entry.MainActivity", "onCreate") in methods
    assert ("com.demo.net.Config", "buildUploadUrl") in methods


def test_hook_search_filters_methods_by_query() -> None:
    index = JavaMethodIndexer().build(Path("tests/fixtures/jadx_sources"))

    upload_matches = HookSearch().search(index, "upload")
    activity_matches = HookSearch().search(index, "MainActivity")

    assert [(item.class_name, item.method_name) for item in upload_matches] == [
        ("com.demo.net.Config", "buildUploadUrl"),
    ]
    assert [(item.class_name, item.method_name) for item in activity_matches] == [
        ("com.demo.entry.MainActivity", "onCreate"),
    ]
