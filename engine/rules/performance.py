#!/usr/bin/env python3
"""Performance Rules — Plugin audit performa kode Pine Script."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {
    "name": "Performance",
    "version": "1.0",
    "author": "Bengkel-Pine",
    "pine_version": 6,
    "description": "Mendeteksi praktik performa (cached security, step loop)"
}

def register(registry):
    registry.add(AuditRule(
        id='BP-P001', name='cached_security', category='performance',
        description='request.security di-cache dengan var — menghindari panggilan berulang',
        points=8, severity=Severity.INFO, priority=10,
        check_fn=lambda ctx: ctx.get('cached_sec', False)
    ))
    registry.add(AuditRule(
        id='BP-P002', name='step_loop', category='performance',
        description='Loop dengan by/step — iterasi efisien',
        points=3, severity=Severity.INFO, priority=20,
        check_fn=lambda ctx: ctx.get('step_loop', False)
    ))
