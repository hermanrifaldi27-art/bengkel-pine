#!/usr/bin/env python3
"""Complexity Rules v2 — Deteksi fungsi panjang dan nesting dalam (dari StatisticsVisitor)."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {"name":"Complexity","version":"2.0","author":"Bengkel-Pine","pine_version":6,"description":"Mendeteksi kompleksitas kode berlebihan"}

def register(registry):
    # Fungsi panjang: gunakan func_count sebagai proxy (semakin banyak fungsi, semakin modular)
    registry.add(AuditRule(
        id='BP-X001', name='function_modularity', category='complexity',
        description='Fungsi kustom ≥ 5 — kode terstruktur modular (fungsi pendek)',
        points=5, severity=Severity.INFO, priority=10,
        check_fn=lambda ctx: ctx.func_count >= 5
    ))
    # Nesting dalam: gunakan switch_count + if_count (dari StatisticsVisitor nanti)
    # Untuk sekarang, gunakan switch_count sebagai proxy kompleksitas
    registry.add(AuditRule(
        id='BP-X002', name='nesting_complexity', category='complexity',
        description='Switch statement terdeteksi — kode menggunakan kontrol alur majemuk',
        points=3, severity=Severity.INFO, priority=20,
        check_fn=lambda ctx: ctx.switch_count >= 1
    ))
