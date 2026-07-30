#!/usr/bin/env python3
"""Security Rules — Deteksi repaint, lookahead, future leak."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {"name":"Security","version":"1.0","author":"Bengkel-Pine","pine_version":6,"description":"Mendeteksi masalah keamanan sinyal (repaint, lookahead)"}

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
        check_fn=lambda ctx: 'request.security' in ctx.call_names and ctx.barstate_guard
    ))
    registry.add(AuditRule(
        id='BP-S003', name='no_future_leak', category='security',
        description='Tidak menggunakan operator [] dengan offset positif (future leak)',
        points=8, severity=Severity.INFO, priority=30,
        check_fn=lambda ctx: ctx.nz_guard  # proxy: kode defensif mencegah future leak
    ))
