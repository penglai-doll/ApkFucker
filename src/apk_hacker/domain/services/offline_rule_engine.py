from __future__ import annotations

from apk_hacker.domain.models.hook_advice import HookRecommendation
from apk_hacker.domain.models.static_inputs import StaticInputs


class OfflineRuleEngine:
    def recommend(self, static_inputs: StaticInputs) -> tuple[HookRecommendation, ...]:
        recommendations: list[HookRecommendation] = []

        if static_inputs.callback_endpoints or any("network" in tag or "webview" in tag for tag in static_inputs.technical_tags):
            recommendations.append(
                HookRecommendation(
                    recommendation_id="template:ssl.okhttp3_unpin",
                    kind="template_hook",
                    title="OkHttp3 SSL Unpinning",
                    reason="Callback / network clues suggest outbound HTTPS traffic that may need certificate bypassing.",
                    score=7,
                    matched_terms=("ssl", "https", "network"),
                    template_id="ssl.okhttp3_unpin",
                    template_name="OkHttp3 SSL Unpinning",
                    plugin_id="builtin.ssl-okhttp3-unpin",
                    source_signals=("callback_endpoints", "technical_tags"),
                    template_event_types=("template_loaded", "ssl_unpinning_bypass", "method_error"),
                    template_category="ssl",
                )
            )

        if static_inputs.crypto_signals:
            recommendations.append(
                HookRecommendation(
                    recommendation_id="template:crypto.cipher_monitor",
                    kind="template_hook",
                    title="Cipher Monitor",
                    reason="Crypto signals were detected in static analysis, so a generic cipher monitor is a strong starting point.",
                    score=6,
                    matched_terms=("crypto", "cipher"),
                    template_id="crypto.cipher_monitor",
                    template_name="Cipher Monitor",
                    plugin_id="builtin.crypto-cipher-monitor",
                    source_signals=("crypto_signals",),
                    template_event_types=("template_loaded", "crypto_call", "crypto_return", "method_error"),
                    template_category="crypto",
                )
            )

        if static_inputs.packer_hints:
            recommendations.append(
                HookRecommendation(
                    recommendation_id="template:anti_detection.frida_detect_bypass",
                    kind="template_hook",
                    title="Frida Detection Bypass",
                    reason="Packer or shell hints suggest anti-analysis checks that often pair with Frida detection logic.",
                    score=5,
                    matched_terms=("frida", "detection", "packer"),
                    template_id="anti_detection.frida_detect_bypass",
                    template_name="Frida Detection Bypass",
                    plugin_id="builtin.anti-detection-frida-bypass",
                    source_signals=("packer_hints",),
                    template_event_types=("template_loaded", "anti_detection_bypass", "method_error"),
                    template_category="anti_detection",
                )
            )

        return tuple(recommendations)
