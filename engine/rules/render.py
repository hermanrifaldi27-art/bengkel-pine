#!/usr/bin/env python3
"""Render Rules — Plugin audit tampilan visual Pine Script."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {
    "name": "Render",
    "version": "1.0",
    "author": "Bengkel-Pine",
    "pine_version": 6,
    "description": "Mendeteksi praktik rendering (overlay, hidden plot, inline, transparansi)"
}

def register(registry):
    registry.add(AuditRule(
        id='BP-V001', name='force_overlay', category='render',
        description='force_overlay=true — tampilan di pane harga',
        points=3, severity=Severity.INFO, priority=10,
        check_fn=lambda ctx: ctx.get('force_overlay', False)
    ))
    registry.add(AuditRule(
        id='BP-V002', name='hidden_plot', category='render',
        description='Plot dengan display.none — kalkulasi tanpa visual berlebih',
        points=5, severity=Severity.INFO, priority=20,
        check_fn=lambda ctx: ctx.get('hidden_plot', False)
    ))
    registry.add(AuditRule(
        id='BP-V003', name='inline_inputs', category='render',
        description='Input dengan inline — hemat ruang panel',
        points=3, severity=Severity.INFO, priority=30,
        check_fn=lambda ctx: ctx.get('inline_inputs', False)
    ))
