#!/usr/bin/env python3
"""Complexity Rules — Deteksi fungsi terlalu panjang dan nesting dalam."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {"name":"Complexity","version":"1.0","author":"Bengkel-Pine","pine_version":6,"description":"Mendeteksi kompleksitas kode"}

def register(registry):
    registry.add(AuditRule(
        id='BP-X001', name='function_length', category='complexity',
        description='Fungsi dengan banyak operasi — pertimbangkan dekomposisi',
        points=0, severity=Severity.WARNING, priority=10,
        check_fn=lambda ctx: ctx.func_count > 0  # Placeholder: perlu AST analysis
    ))
    registry.add(AuditRule(
        id='BP-X002', name='nesting_depth', category='complexity',
        description='Nesting dalam terdeteksi — hindari >3 tingkat if/for bersarang',
        points=0, severity=Severity.WARNING, priority=20,
        check_fn=lambda ctx: ctx.switch_count > 0  # Proxy: switch = kompleksitas
    ))
