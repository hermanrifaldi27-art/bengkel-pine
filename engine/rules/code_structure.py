#!/usr/bin/env python3
"""Code Structure Rules — Deteksi struktur kode yang baik."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {"name":"Code Structure","version":"1.0","author":"Bengkel-Pine","pine_version":6,"description":"Mendeteksi praktik struktur kode"}

def register(registry):
    registry.add(AuditRule(
        id='BP-C001', name='function_count', category='code_structure',
        description='Jumlah fungsi kustom >= 3 — kode terstruktur modular',
        points=3, severity=Severity.INFO, priority=10,
        check_fn=lambda ctx: ctx.func_count >= 3
    ))
    registry.add(AuditRule(
        id='BP-C002', name='type_usage', category='code_structure',
        description='Menggunakan type/struct — kode terorganisir',
        points=5, severity=Severity.INFO, priority=20,
        check_fn=lambda ctx: ctx.types_count >= 1
    ))
    registry.add(AuditRule(
        id='BP-C003', name='method_usage', category='code_structure',
        description='Method pada type — enkapsulasi baik',
        points=5, severity=Severity.INFO, priority=30,
        check_fn=lambda ctx: ctx.methods_count >= 2
    ))
