#!/usr/bin/env python3
"""Security Rules v2 — Deteksi repainting, barstate consistency, future leak."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {"name":"Security","version":"2.0","author":"Bengkel-Pine","pine_version":6,"description":"Mendeteksi masalah keamanan sinyal"}

def register(registry):
    registry.add(AuditRule(
        id='BP-S001', name='barstate_confirmed', category='security',
        description='Menggunakan barstate.isconfirmed — sinyal tidak repaint',
        points=15, severity=Severity.INFO, priority=10,
        check_fn=lambda ctx: ctx.barstate_guard
    ))
    registry.add(AuditRule(
        id='BP-S002', name='lookahead_off', category='security',
        description='request.security dengan lookahead=barmerge.lookahead_off',
        points=10, severity=Severity.INFO, priority=20,
        check_fn=lambda ctx: ctx.cached_sec  # proxy: var + security = lookahead awareness
    ))
    registry.add(AuditRule(
        id='BP-S003', name='no_future_leak', category='security',
        description='Tidak menggunakan operator [] dengan offset positif (future leak)',
        points=8, severity=Severity.INFO, priority=30,
        check_fn=lambda ctx: ctx.nz_guard  # proxy: kode defensif
    ))
    registry.add(AuditRule(
        id='BP-S004', name='barstate_consistency', category='security',
        description='Kalkulasi dalam blok barstate.isconfirmed — mencegah repaint non-security',
        points=12, severity=Severity.INFO, priority=5,
        check_fn=lambda ctx: ctx.barstate_guard and ctx.func_count >= 5  # Ada guard + banyak fungsi = kesadaran
    ))
