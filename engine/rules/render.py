#!/usr/bin/env python3
"""Render Rules — Plugin audit tampilan visual."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {"name":"Render","version":"1.2","author":"Bengkel-Pine","pine_version":6,"description":"Mendeteksi praktik rendering"}

def register(registry):
    registry.add(AuditRule('BP-V001','force_overlay','render','force_overlay=true',3,Severity.INFO,10,lambda ctx: ctx.force_overlay))
    registry.add(AuditRule('BP-V002','hidden_plot','render','Plot display.none',5,Severity.INFO,20,lambda ctx: ctx.hidden_plot))
    registry.add(AuditRule('BP-V003','inline_inputs','render','Input inline',3,Severity.INFO,30,lambda ctx: ctx.inline_inputs))
