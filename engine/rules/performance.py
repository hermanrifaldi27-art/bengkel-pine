#!/usr/bin/env python3
"""Performance Rules — Deteksi praktik performa: cached security, loop step."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {"name":"Performance","version":"2.0","author":"Bengkel-Pine","pine_version":6,"description":"Mendeteksi praktik performa"}

def register(registry):
    registry.add(AuditRule(
        id='BP-P001', name='cached_security', category='performance',
        description='request.security di-cache dengan var — hindari panggilan berulang',
        points=8, severity=Severity.INFO, priority=10,
        check_fn=lambda ctx: ctx.cached_sec
    ))
    registry.add(AuditRule(
        id='BP-P002', name='step_loop', category='performance',
        description='Loop dengan by/step — iterasi efisien',
        points=3, severity=Severity.INFO, priority=20,
        check_fn=lambda ctx: ctx.step_loop
    ))
    registry.add(AuditRule(
        id='BP-P003', name='security_lower_tf_cached', category='performance',
        description='request.security_lower_tf di-cache — hindari multiple TF requests',
        points=10, severity=Severity.INFO, priority=5,
        check_fn=lambda ctx: 'request.security_lower_tf' in ctx.call_names
    ))
