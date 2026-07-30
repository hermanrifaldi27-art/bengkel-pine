#!/usr/bin/env python3
"""
Diagnostic Engine v1.0
Severity, code, range, hint, quick fix
"""
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from enum import Enum
from engine.parser import SourceSpan


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


@dataclass
class QuickFix:
    title: str
    edit: str  # kode pengganti
    apply: Optional[Callable] = None  # fungsi untuk apply fix


@dataclass
class Diagnostic:
    code: str           # e.g., "PINE0001"
    message: str
    severity: Severity
    span: Optional[SourceSpan] = None
    hint: Optional[str] = None
    quick_fixes: List[QuickFix] = field(default_factory=list)

    def __repr__(self):
        loc = f"line {self.span.start_line}:{self.span.start_col}" if self.span else "unknown"
        return f"[{self.severity.value.upper()}] {self.code} at {loc}: {self.message}"


class DiagnosticEngine:
    def __init__(self):
        self.diagnostics: List[Diagnostic] = []

    def add(self, diag: Diagnostic):
        self.diagnostics.append(diag)

    def error(self, code: str, message: str, span: Optional[SourceSpan] = None, hint: Optional[str] = None):
        self.add(Diagnostic(code, message, Severity.ERROR, span, hint))

    def warning(self, code: str, message: str, span: Optional[SourceSpan] = None, hint: Optional[str] = None):
        self.add(Diagnostic(code, message, Severity.WARNING, span, hint))

    def info(self, code: str, message: str, span: Optional[SourceSpan] = None, hint: Optional[str] = None):
        self.add(Diagnostic(code, message, Severity.INFO, span, hint))

    def has_errors(self) -> bool:
        return any(d.severity == Severity.ERROR for d in self.diagnostics)

    def get_all(self) -> List[Diagnostic]:
        return self.diagnostics

    def clear(self):
        self.diagnostics = []
