#!/usr/bin/env python3
"""Performance Rules — Plugin audit performa."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {"name":"Performance","version":"1.2","author":"Bengkel-Pine","pine_version":6,"description":"Mendeteksi praktik performa"}

def register(registry):
    registry.add(AuditRule('BP-P001','cached_security','performance','Security di-cache dengan var',8,Severity.INFO,10,lambda ctx: ctx.cached_sec))
    registry.add(AuditRule('BP-P002','step_loop','performance','Loop dengan step',3,Severity.INFO,20,lambda ctx: ctx.step_loop))
