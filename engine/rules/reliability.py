#!/usr/bin/env python3
"""Reliability Rules — Plugin audit keandalan kode Pine Script."""
from engine.audit.registry import AuditRule
from engine.config import Severity

PLUGIN_META = {"name":"Reliability","version":"2.2","author":"Bengkel-Pine","pine_version":6,"description":"Mendeteksi praktik keandalan kode"}

def register(registry):
    registry.add(AuditRule('BP-R001','barstate_guard','reliability','Menggunakan barstate.isconfirmed/ishistory',15,Severity.INFO,10,lambda ctx: ctx.barstate_guard))
    registry.add(AuditRule('BP-R002','na_guard','reliability','Menggunakan na() guard',8,Severity.INFO,20,lambda ctx: ctx.na_guard))
    registry.add(AuditRule('BP-R003','nz_guard','reliability','Menggunakan nz() fallback',5,Severity.INFO,30,lambda ctx: ctx.nz_guard))
    registry.add(AuditRule('BP-R004','nan_check','reliability','Pengecekan math.is_nan / math.is_finite',5,Severity.INFO,40,lambda ctx: ctx.nan_check))
