#!/usr/bin/env python3
"""AuditContext — Immutable, type-safe, backward-compatible."""
from dataclasses import dataclass, field, asdict
from typing import List, Any

@dataclass(frozen=True)
class AuditContext:
    """Konteks audit yang dibangun dari AST dan kode sumber.
    Mendukung akses: ctx.field, ctx['field'], ctx.get('field', default)."""

    # ── RELIABILITY ──
    barstate_guard: bool = False
    na_guard: bool = False
    nz_guard: bool = False
    nan_check: bool = False

    # ── MEMORY ──
    var_count: int = 0
    global_var_count: int = 0
    array_eviction: bool = False
    matrix_eviction: bool = False
    drawing_limits: bool = False
    bars_back_limit: bool = False

    # ── PERFORMANCE ──
    cached_sec: bool = False
    step_loop: bool = False

    # ── RENDER ──
    force_overlay: bool = False
    hidden_plot: bool = False
    inline_inputs: bool = False
    transparency: bool = False

    # ── DEBUG ──
    alert_cond: bool = False
    alert_func: bool = False
    logging: bool = False

    # ── SCOPE ──
    export: bool = False

    # ── TYPE SAFETY ──
    typed_inputs: bool = False
    typed_fields: bool = False

    # ── UX ──
    tooltip_count: int = 0
    input_groups: bool = False

    # ── READABILITY ──
    structured_comments: bool = False
    documented_code: bool = False

    # ── STATISTICS ──
    types_count: int = 0
    methods_count: int = 0
    func_count: int = 0
    switch_count: int = 0
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0

    # ── CALL TRACKING ──
    call_names: List[str] = field(default_factory=list)

    # ── COMPATIBILITY: dict-like access ──
    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def keys(self):
        return asdict(self).keys()

    def values(self):
        return asdict(self).values()

    def items(self):
        return asdict(self).items()

    def to_dict(self) -> dict:
        return asdict(self)
