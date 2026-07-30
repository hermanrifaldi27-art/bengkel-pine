#!/usr/bin/env python3
"""Memory Rules — Plugin audit manajemen memori."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {
    "name": "Memory",
    "version": "2.0",
    "author": "Bengkel-Pine",
    "pine_version": 6,
    "description": "Mendeteksi praktik manajemen memori (var, array eviction, matrix eviction)"
}

def register(registry):
    registry.add(AuditRule(
        id='BP-M001', name='var_usage', category='memory',
        description='Deklarasi var ≥ 10 — state persistent dikelola baik',
        points=3, severity=Severity.INFO, priority=10,
        check_fn=lambda ctx: ctx.get('var_count', 0) >= 10
    ))
    registry.add(AuditRule(
        id='BP-M002', name='array_eviction', category='memory',
        description='Array push + shift/pop — ukuran terkendali, mencegah memory leak',
        points=12, severity=Severity.INFO, priority=20,
        check_fn=lambda ctx: ctx.get('array_eviction', False)
    ))
    registry.add(AuditRule(
        id='BP-M003', name='matrix_eviction', category='memory',
        description='Matrix add_row + remove_row — ukuran terkendali',
        points=12, severity=Severity.INFO, priority=30,
        check_fn=lambda ctx: ctx.get('matrix_eviction', False)
    ))
    registry.add(AuditRule(
        id='BP-M004', name='drawing_limits', category='memory',
        description='Batasan max_labels/lines/boxes_count eksplisit',
        points=5, severity=Severity.INFO, priority=40,
        check_fn=lambda ctx: ctx.get('drawing_limits', False)
    ))
