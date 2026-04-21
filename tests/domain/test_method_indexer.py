from __future__ import annotations

from pathlib import Path

from apk_hacker.domain.services.method_indexer import JavaMethodIndexer


def test_java_method_indexer_extracts_multiline_and_nested_methods(tmp_path: Path) -> None:
    source_root = tmp_path / "jadx"
    source_file = source_root / "com" / "demo" / "edge" / "LoginActivity.java"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        """
package com.demo.edge;

import java.io.IOException;
import java.util.Map;

public class LoginActivity {
    @JavascriptInterface
    public final String buildSignedPayload(
            String host,
            Map<String, String> headers
    ) throws IOException {
        return host + headers.size();
    }

    private static <T> T decode(
            T value
    ) {
        return value;
    }

    class InnerWorker {
        void postLogin(
                String token
        ) {
            System.out.println(token);
        }
    }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    index = JavaMethodIndexer().build(source_root)

    methods_by_name = {f"{item.class_name}.{item.method_name}": item for item in index.methods}

    signed_payload = methods_by_name["com.demo.edge.LoginActivity.buildSignedPayload"]
    decode = methods_by_name["com.demo.edge.LoginActivity.decode"]
    post_login = methods_by_name["com.demo.edge.LoginActivity$InnerWorker.postLogin"]

    assert signed_payload.parameter_types == ("String", "Map<String, String>")
    assert signed_payload.return_type == "String"
    assert "buildSignedPayload(" in signed_payload.declaration
    assert "Map<String, String> headers" in signed_payload.declaration
    assert "return host + headers.size();" in signed_payload.source_preview

    assert decode.parameter_types == ("T",)
    assert decode.return_type == "T"
    assert decode.declaration.startswith("private static <T> T decode(")

    assert post_login.parameter_types == ("String",)
    assert post_login.class_name == "com.demo.edge.LoginActivity$InnerWorker"
    assert "System.out.println(token);" in post_login.source_preview


def test_java_method_indexer_keeps_methods_without_package_declaration(tmp_path: Path) -> None:
    source_root = tmp_path / "jadx"
    source_file = source_root / "orphan" / "NoPackage.java"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        """
public class NoPackage {
    public String revealSecret(
            String token
    ) {
        return "secret:" + token;
    }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    index = JavaMethodIndexer().build(source_root)

    methods_by_name = {f"{item.class_name}.{item.method_name}": item for item in index.methods}
    reveal_secret = methods_by_name["orphan.NoPackage.revealSecret"]

    assert reveal_secret.parameter_types == ("String",)
    assert reveal_secret.return_type == "String"
    assert reveal_secret.source_path == "orphan/NoPackage.java"
    assert "return \"secret:\" + token;" in reveal_secret.source_preview


def test_java_method_indexer_handles_inline_annotations_and_complex_generics(tmp_path: Path) -> None:
    source_root = tmp_path / "jadx"
    source_file = source_root / "com" / "demo" / "edge" / "SignatureEdgeCases.java"
    source_file.parent.mkdir(parents=True)
    source_file.write_text(
        """
package com.demo.edge;

import java.io.Serializable;
import java.util.List;
import java.util.Map;

public class SignatureEdgeCases {
    @androidx.annotation.Nullable public static <T extends Serializable & Comparable<T>> Map<String, ? extends T> resolvePayload(
            final List<? extends T> values,
            @androidx.annotation.NonNull String... names
    ) throws IllegalStateException {
        return null;
    }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    index = JavaMethodIndexer().build(source_root)

    methods_by_name = {f"{item.class_name}.{item.method_name}": item for item in index.methods}
    resolve_payload = methods_by_name["com.demo.edge.SignatureEdgeCases.resolvePayload"]

    assert resolve_payload.return_type == "Map<String, ? extends T>"
    assert resolve_payload.parameter_types == ("List<? extends T>", "String...")
    assert resolve_payload.declaration.startswith(
        "@androidx.annotation.Nullable public static <T extends Serializable & Comparable<T>> Map<String, ? extends T> resolvePayload("
    )


def test_java_method_indexer_prefers_matching_package_prefixes(tmp_path: Path) -> None:
    source_root = tmp_path / "jadx"
    app_file = source_root / "com" / "demo" / "app" / "MainActivity.java"
    library_file = source_root / "okhttp3" / "CertificatePinner.java"
    app_file.parent.mkdir(parents=True)
    library_file.parent.mkdir(parents=True)

    app_file.write_text(
        """
package com.demo.app;

public class MainActivity {
    public String buildPayload(String token) {
        return token;
    }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    library_file.write_text(
        """
package okhttp3;

public class CertificatePinner {
    public void check(String host) {
    }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    index = JavaMethodIndexer().build(source_root, package_prefixes=("com.demo.app",))

    assert [item.class_name for item in index.classes] == ["com.demo.app.MainActivity"]
    assert [f"{item.class_name}.{item.method_name}" for item in index.methods] == [
        "com.demo.app.MainActivity.buildPayload"
    ]
