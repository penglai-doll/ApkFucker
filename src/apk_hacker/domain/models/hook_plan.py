from __future__ import annotations

from dataclasses import dataclass

from apk_hacker.domain.models.indexes import MethodIndexEntry


@dataclass(frozen=True, slots=True)
class HookPlanSource:
    source_id: str
    kind: str
    source_kind: str | None = None
    method: MethodIndexEntry | None = None
    script_name: str | None = None
    script_path: str | None = None
    template_id: str | None = None
    template_name: str | None = None
    plugin_id: str | None = None
    reason: str | None = None
    matched_terms: tuple[str, ...] = ()
    source_signals: tuple[str, ...] = ()
    template_event_types: tuple[str, ...] = ()
    template_category: str | None = None
    requires_root: bool = False
    supports_offline: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "matched_terms", tuple(str(value) for value in self.matched_terms))
        object.__setattr__(self, "source_signals", tuple(str(value) for value in self.source_signals))
        object.__setattr__(
            self,
            "template_event_types",
            tuple(str(value) for value in self.template_event_types),
        )

    @classmethod
    def from_method(
        cls,
        method: MethodIndexEntry,
        *,
        source_kind: str = "selected_method",
        reason: str | None = None,
        matched_terms: tuple[str, ...] = (),
        source_signals: tuple[str, ...] = (),
    ) -> "HookPlanSource":
        signature = ",".join(method.parameter_types)
        return cls(
            source_id=f"method:{method.class_name}:{method.method_name}:{signature}:{method.source_path}",
            kind="method_hook",
            source_kind=source_kind,
            method=method,
            reason=reason,
            matched_terms=matched_terms,
            source_signals=source_signals,
        )

    @classmethod
    def from_custom_script(
        cls,
        script_name: str,
        script_path: str,
        *,
        source_kind: str = "custom_script",
    ) -> "HookPlanSource":
        return cls(
            source_id=f"custom_script:{script_path}",
            kind="custom_script",
            source_kind=source_kind,
            script_name=script_name,
            script_path=script_path,
        )

    @classmethod
    def from_template(
        cls,
        template_id: str,
        template_name: str,
        plugin_id: str,
        *,
        source_kind: str = "framework_plugin",
        reason: str | None = None,
        matched_terms: tuple[str, ...] = (),
        source_signals: tuple[str, ...] = (),
        template_event_types: tuple[str, ...] = (),
        template_category: str | None = None,
        requires_root: bool = False,
        supports_offline: bool = True,
    ) -> "HookPlanSource":
        return cls(
            source_id=f"template:{plugin_id}:{template_id}",
            kind="template_hook",
            source_kind=source_kind,
            template_id=template_id,
            template_name=template_name,
            plugin_id=plugin_id,
            reason=reason,
            matched_terms=matched_terms,
            source_signals=source_signals,
            template_event_types=template_event_types,
            template_category=template_category,
            requires_root=requires_root,
            supports_offline=supports_offline,
        )

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "source_id": self.source_id,
            "kind": self.kind,
            "source_kind": self.source_kind,
        }
        if self.method is not None:
            payload["method"] = self.method.to_payload()
        if self.script_name is not None:
            payload["script_name"] = self.script_name
        if self.script_path is not None:
            payload["script_path"] = self.script_path
        if self.template_id is not None:
            payload["template_id"] = self.template_id
        if self.template_name is not None:
            payload["template_name"] = self.template_name
        if self.plugin_id is not None:
            payload["plugin_id"] = self.plugin_id
        if self.reason is not None:
            payload["reason"] = self.reason
        if self.matched_terms:
            payload["matched_terms"] = list(self.matched_terms)
        if self.source_signals:
            payload["source_signals"] = list(self.source_signals)
        if self.template_event_types:
            payload["template_event_types"] = list(self.template_event_types)
        if self.template_category is not None:
            payload["template_category"] = self.template_category
        if self.requires_root:
            payload["requires_root"] = self.requires_root
        if not self.supports_offline:
            payload["supports_offline"] = self.supports_offline
        return payload

    @classmethod
    def from_payload(cls, payload: object) -> "HookPlanSource | None":
        if not isinstance(payload, dict):
            return None
        source_id = payload.get("source_id")
        kind = payload.get("kind")
        if not isinstance(source_id, str) or not isinstance(kind, str):
            return None
        return cls(
            source_id=source_id,
            kind=kind,
            source_kind=str(payload["source_kind"]) if isinstance(payload.get("source_kind"), str) else None,
            method=MethodIndexEntry.from_payload(payload.get("method")),
            script_name=str(payload["script_name"]) if isinstance(payload.get("script_name"), str) else None,
            script_path=str(payload["script_path"]) if isinstance(payload.get("script_path"), str) else None,
            template_id=str(payload["template_id"]) if isinstance(payload.get("template_id"), str) else None,
            template_name=str(payload["template_name"]) if isinstance(payload.get("template_name"), str) else None,
            plugin_id=str(payload["plugin_id"]) if isinstance(payload.get("plugin_id"), str) else None,
            reason=str(payload["reason"]) if isinstance(payload.get("reason"), str) else None,
            matched_terms=tuple(str(value) for value in payload.get("matched_terms", []) or []),
            source_signals=tuple(str(value) for value in payload.get("source_signals", []) or []),
            template_event_types=tuple(str(value) for value in payload.get("template_event_types", []) or []),
            template_category=str(payload["template_category"]) if isinstance(payload.get("template_category"), str) else None,
            requires_root=bool(payload.get("requires_root", False)),
            supports_offline=bool(payload.get("supports_offline", True)),
        )


@dataclass(frozen=True, slots=True)
class MethodHookTarget:
    target_id: str
    class_name: str
    method_name: str
    parameter_types: tuple[str, ...]
    return_type: str
    source_origin: str
    notes: str = ""

    def to_payload(self) -> dict[str, object]:
        return {
            "target_id": self.target_id,
            "class_name": self.class_name,
            "method_name": self.method_name,
            "parameter_types": list(self.parameter_types),
            "return_type": self.return_type,
            "source_origin": self.source_origin,
            "notes": self.notes,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "MethodHookTarget | None":
        if not isinstance(payload, dict):
            return None
        target_id = payload.get("target_id")
        class_name = payload.get("class_name")
        method_name = payload.get("method_name")
        return_type = payload.get("return_type")
        source_origin = payload.get("source_origin")
        if not all(isinstance(value, str) for value in (target_id, class_name, method_name, return_type, source_origin)):
            return None
        parameter_types = payload.get("parameter_types", [])
        return cls(
            target_id=str(target_id),
            class_name=str(class_name),
            method_name=str(method_name),
            parameter_types=tuple(str(value) for value in parameter_types) if isinstance(parameter_types, list) else (),
            return_type=str(return_type),
            source_origin=str(source_origin),
            notes=str(payload.get("notes", "")),
        )


@dataclass(frozen=True, slots=True)
class HookPlanItem:
    item_id: str
    kind: str
    source_kind: str
    enabled: bool
    inject_order: int
    target: MethodHookTarget | None
    render_context: dict[str, object]
    plugin_id: str | None = None
    template_id: str | None = None
    evidence_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    reason: str | None = None
    matched_terms: tuple[str, ...] = ()
    source_signals: tuple[str, ...] = ()
    template_event_types: tuple[str, ...] = ()
    template_category: str | None = None
    requires_root: bool = False
    supports_offline: bool = True

    def to_payload(self) -> dict[str, object]:
        return {
            "item_id": self.item_id,
            "kind": self.kind,
            "source_kind": self.source_kind,
            "enabled": self.enabled,
            "inject_order": self.inject_order,
            "target": self.target.to_payload() if self.target is not None else None,
            "render_context": dict(self.render_context),
            "plugin_id": self.plugin_id,
            "template_id": self.template_id,
            "evidence_ids": list(self.evidence_ids),
            "tags": list(self.tags),
            "reason": self.reason,
            "matched_terms": list(self.matched_terms),
            "source_signals": list(self.source_signals),
            "template_event_types": list(self.template_event_types),
            "template_category": self.template_category,
            "requires_root": self.requires_root,
            "supports_offline": self.supports_offline,
        }

    @classmethod
    def from_payload(cls, payload: object) -> "HookPlanItem | None":
        if not isinstance(payload, dict):
            return None
        item_id = payload.get("item_id")
        kind = payload.get("kind")
        if not isinstance(item_id, str) or not isinstance(kind, str):
            return None
        render_context = payload.get("render_context", {})
        if not isinstance(render_context, dict):
            render_context = {}
        return cls(
            item_id=item_id,
            kind=kind,
            source_kind=str(payload["source_kind"]) if isinstance(payload.get("source_kind"), str) else kind,
            enabled=bool(payload.get("enabled", True)),
            inject_order=int(payload.get("inject_order", 0)),
            target=MethodHookTarget.from_payload(payload.get("target")),
            render_context={str(key): value for key, value in render_context.items()},
            plugin_id=str(payload["plugin_id"]) if isinstance(payload.get("plugin_id"), str) else None,
            template_id=str(payload["template_id"]) if isinstance(payload.get("template_id"), str) else None,
            evidence_ids=tuple(str(value) for value in payload.get("evidence_ids", []) or []),
            tags=tuple(str(value) for value in payload.get("tags", []) or []),
            reason=str(payload["reason"]) if isinstance(payload.get("reason"), str) else None,
            matched_terms=tuple(str(value) for value in payload.get("matched_terms", []) or []),
            source_signals=tuple(str(value) for value in payload.get("source_signals", []) or []),
            template_event_types=tuple(str(value) for value in payload.get("template_event_types", []) or []),
            template_category=str(payload["template_category"]) if isinstance(payload.get("template_category"), str) else None,
            requires_root=bool(payload.get("requires_root", False)),
            supports_offline=bool(payload.get("supports_offline", True)),
        )


@dataclass(frozen=True, slots=True)
class HookPlan:
    items: tuple[HookPlanItem, ...]

    def to_payload(self) -> dict[str, object]:
        return {"items": [item.to_payload() for item in self.items]}

    @classmethod
    def from_payload(cls, payload: object) -> "HookPlan":
        if not isinstance(payload, dict):
            return cls(items=())
        items_payload = payload.get("items", [])
        if not isinstance(items_payload, list):
            items_payload = []
        return cls(
            items=tuple(
                item
                for item in (HookPlanItem.from_payload(entry) for entry in items_payload)
                if item is not None
            )
        )
