#!/usr/bin/env python3
"""Memory Rules — Plugin audit manajemen memori."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {"name":"Memory","version":"2.2","author":"Bengkel-Pine","pine_version":6,"description":"Mendeteksi praktik manajemen memori"}

def register(registry):
    registry.add(AuditRule('BP-M001','var_usage','memory','Deklarasi var >= 10',3,Severity.INFO,10,lambda ctx: ctx.var_count >= 10))
    registry.add(AuditRule('BP-M002','array_eviction','memory','Array push + shift/pop',12,Severity.INFO,20,lambda ctx: ctx.array_eviction))
    registry.add(AuditRule('BP-M003','matrix_eviction','memory','Matrix add_row + remove_row',12,Severity.INFO,30,lambda ctx: ctx.matrix_eviction))
    registry.add(AuditRule('BP-M004','drawing_limits','memory','Batasan drawing eksplisit',5,Severity.INFO,40,lambda ctx: ctx.drawing_limits))
