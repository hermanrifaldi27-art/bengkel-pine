from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

class Severity(str, Enum):
    error = "error"
    warning = "warning"
    info = "info"

@dataclass
class LintIssue:
    rule_id: str
    severity: Severity
    message: str
    line: Optional[int] = None
    snippet: Optional[str] = None
    fix_hint: Optional[str] = None

    def format(self) -> str:
        loc = f"line {self.line}: " if self.line else ""
        icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[self.severity.value]
        out = f"{icon} [{self.rule_id}] {loc}{self.message}"
        if self.fix_hint:
            out += f"\n   💡 {self.fix_hint}"
        return out

@dataclass
class LintReport:
    issues: List[LintIssue] = field(default_factory=list)
    file_path: Optional[str] = None

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.error)
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.warning)
    @property
    def health(self) -> str:
        if self.error_count: return "CRITICAL"
        if self.warning_count: return "WARNING"
        return "OK"

    def format(self) -> str:
        header = f"=== PINELINT === Health: {self.health}"
        if self.file_path: header += f" ({self.file_path})"
        header += f" — {self.error_count} error, {self.warning_count} warning\n"
        if not self.issues: return header + "✅ Tidak ada isu terdeteksi.\n"
        body = "\n".join(i.format() for i in self.issues)
        return header + body + "\n"

def _line_of(code: str, pos: int) -> int:
    return code[:pos].count("\n") + 1
def _snippet_at(code: str, pos: int) -> str:
    lines = code.splitlines()
    idx = _line_of(code, pos) - 1
    if 0 <= idx < len(lines): return lines[idx].strip()
    return ""

class PineLinter:
    def lint(self, code: str, file_path: Optional[str] = None) -> LintReport:
        report = LintReport(file_path=file_path)
        self._check_version(code, report)
        self._check_repainting(code, report)
        self._check_lookahead(code, report)
        self._check_missing_stoploss(code, report)
        self._check_array_unbounded(code, report)
        self._check_matrix_unbounded(code, report)
        self._check_plot_in_local_scope(code, report)
        self._check_var_in_function(code, report)
        self._check_na_comparison(code, report)
        self._check_security_lookahead(code, report)
        self._check_alert_without_confirmed(code, report)
        return report
    def lint_file(self, path: str) -> LintReport:
        with open(path, "r", encoding="utf-8") as f: code = f.read()
        return self.lint(code, file_path=path)
    def _check_version(self, code, report):
        if not re.search(r"//@version\s*=\s*[56]", code):
            report.issues.append(LintIssue("lint.version", Severity.warning, "Tidak ada //@version=5/6", fix_hint="Tambahkan //@version=6"))
    def _check_repainting(self, code, report):
        for m in re.finditer(r"request\.security\s*\([^)]*[\"'](\d+[STsmhDWM]?)[\"']", code):
            tf = m.group(1)
            if re.match(r"^\d+[ST]$", tf) or tf in ("1", "1S", "5"):
                report.issues.append(LintIssue("lint.repainting", Severity.warning, f"request.security timeframe '{tf}' repainting risk", line=_line_of(code, m.start()), snippet=_snippet_at(code, m.start()), fix_hint="Gunakan timeframe.period atau lookahead_off"))
    def _check_lookahead(self, code, report):
        if "strategy.entry" not in code: return
        for m in re.finditer(r"\b(close|high|low|open)\s*([><=!]+)\s*(close|high|low|open)(?!\[)", code):
            report.issues.append(LintIssue("lint.lookahead", Severity.warning, "Perbandingan harga bar berjalan di strategi — potensi look-ahead", line=_line_of(code, m.start()), snippet=_snippet_at(code, m.start()), fix_hint="Gunakan close[1] atau barstate.isconfirmed"))
    def _check_missing_stoploss(self, code, report):
        if "strategy(" in code and "strategy.exit" not in code and "strategy.close" not in code:
            report.issues.append(LintIssue("lint.missing_stoploss", Severity.error, "Strategy tanpa stop loss", fix_hint="Tambahkan strategy.exit(..., stop=...)"))
    def _check_array_unbounded(self, code, report):
        if "array.push" not in code: return
        has_eviction = bool(re.search(r"array\.(shift|pop|remove|slice)\s*\(", code) or re.search(r"while\s+array\.size", code))
        if not has_eviction and re.search(r"var\s+\w+\s*=\s*array\.new", code):
            report.issues.append(LintIssue("lint.array_unbounded", Severity.warning, "var array tanpa eviction (shift/remove)", fix_hint="Tambahkan: while array.size(arr) > limit\n    array.shift(arr)"))
    def _check_matrix_unbounded(self, code, report):
        if "matrix.add_row" not in code: return
        has_eviction = bool(re.search(r"matrix\.remove_row\s*\(", code))
        if not has_eviction and re.search(r"var\s+.*matrix\.new", code):
            report.issues.append(LintIssue("lint.matrix_unbounded", Severity.warning, "var matrix tanpa remove_row", fix_hint="Tambahkan: if matrix.rows(m) > limit\n    matrix.remove_row(m,0)"))
    def _check_plot_in_local_scope(self, code, report):
        for m in re.finditer(r"(?:if|for|while)\s+[^\n]+\n(?:[ \t]+[^\n]+\n)*?[ \t]+(plot(?:shape|char|candle)?)\s*\(", code):
            report.issues.append(LintIssue("lint.plot_local_scope", Severity.error, f"{m.group(1)}() di dalam local block", line=_line_of(code, m.start(1)), snippet=_snippet_at(code, m.start(1)), fix_hint="Pindahkan plot ke global scope"))
    def _check_var_in_function(self, code, report):
        for m in re.finditer(r"(\w+)\s*\([^)]*\)\s*=>\s*\{[^}]*\bvar\b", code, re.DOTALL):
            report.issues.append(LintIssue("lint.var_in_function", Severity.error, f"Keyword 'var' di dalam fungsi '{m.group(1)}'", line=_line_of(code, m.start()), fix_hint="Pindahkan deklarasi var ke global/STATE"))
    def _check_na_comparison(self, code, report):
        for m in re.finditer(r"\b\w+\s*(==|!=)\s*na\b|\bna\s*(==|!=)\s*\w+", code):
            report.issues.append(LintIssue("lint.na_comparison", Severity.error, "Perbandingan dengan na memakai == / != — gunakan na()", line=_line_of(code, m.start()), snippet=_snippet_at(code, m.start()), fix_hint="Ganti `x == na` menjadi `na(x)`"))
    def _check_security_lookahead(self, code, report):
        for m in re.finditer(r"request\.security\s*\(([^)]*)\)", code):
            args = m.group(1)
            if "lookahead" not in args and "barmerge.lookahead_off" not in args:
                report.issues.append(LintIssue("lint.security_lookahead", Severity.info, "request.security tanpa lookahead_off", line=_line_of(code, m.start()), snippet=_snippet_at(code, m.start()), fix_hint="Tambahkan lookahead=barmerge.lookahead_off"))
    def _check_alert_without_confirmed(self, code, report):
        if ("alert(" in code or "alertcondition(" in code) and "barstate.isconfirmed" not in code:
            report.issues.append(LintIssue("lint.alert_unconfirmed", Severity.warning, "alert tanpa barstate.isconfirmed", fix_hint="Bungkus: if barstate.isconfirmed\n    alert(...)"))

def lint_file(path: str) -> LintReport:
    return PineLinter().lint_file(path)
