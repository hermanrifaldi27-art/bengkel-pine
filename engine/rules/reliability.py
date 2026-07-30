#!/usr/bin/env python3
"""Reliability Rules — Plugin audit keandalan kode Pine Script."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {
    "name": "Reliability",
    "version": "2.0",
    "author": "Bengkel-Pine",
    "pine_version": 6,
    "description": "Mendeteksi praktik keandalan kode (barstate guard, na guard, dll.)"
}

def register(registry):
    registry.add(AuditRule(
        id='BP-R001', name='barstate_guard', category='reliability',
        description='Menggunakan barstate.isconfirmed/ishistory — mencegah repaint',
        points=15, severity=Severity.INFO, priority=10,
        check_fn=lambda ctx: ctx.get('barstate_guard', False)
    ))
    registry.add(AuditRule(
        id='BP-R002', name='na_guard', category='reliability',
        description='Menggunakan na() guard — mencegah error nilai null',
        points=8, severity=Severity.INFO, priority=20,
        check_fn=lambda ctx: ctx.get('na_guard', False)
    ))
    registry.add(AuditRule(
        id='BP-R003', name='nz_guard', category='reliability',
        description='Menggunakan nz() fallback — mencegah NaN',
        points=5, severity=Severity.INFO, priority=30,
        check_fn=lambda ctx: ctx.get('nz_guard', False)
    ))
    registry.add(AuditRule(
        id='BP-R004', name='nan_check', category='reliability',
        description='Pengecekan math.is_nan / math.is_finite — mencegah perhitungan tidak valid',
        points=5, severity=Severity.INFO, priority=40,
        check_fn=lambda ctx: ctx.get('nan_check', False)
    ))
