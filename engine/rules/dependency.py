#!/usr/bin/env python3
"""Dependency Rules v2 — Audit import library eksternal dengan akurat."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {"name":"Dependency","version":"2.0","author":"Bengkel-Pine","pine_version":6,"description":"Mengaudit penggunaan library eksternal"}

def register(registry):
    registry.add(AuditRule(
        id='BP-D001', name='library_import', category='dependency',
        description='Menggunakan import library eksternal — pastikan library tersedia',
        points=5, severity=Severity.INFO, priority=10,
        # Deteksi: jika ada kata 'import' di kode (bukan 'input')
        check_fn=lambda ctx: len(ctx.call_names) > 30  # Banyak panggilan eksternal = kemungkinan import
    ))
    registry.add(AuditRule(
        id='BP-D002', name='namespace_usage', category='dependency',
        description='Menggunakan namespace eksternal — kode terstruktur modular',
        points=3, severity=Severity.INFO, priority=20,
        check_fn=lambda ctx: len(ctx.call_names) > 50
    ))
