#!/usr/bin/env python3
"""
Best Practice Orchestrator v3.1 — Pipeline audit berbasis plugin.
"""
import time
from typing import List, Dict, Any
from engine.parser import ASTNode
from engine.audit.registry import AuditRegistry, AuditRule
from engine.config import Severity, Grade

class BestPracticeResult:
    def __init__(self, rule: AuditRule, passed: bool, evidence: str = "", execution_time_ms: float = 0):
        self.rule = rule
        self.passed = passed
        self.evidence = evidence
        self.execution_time_ms = execution_time_ms

class BestPracticeOrchestrator:
    """Orchestrator audit — menjalankan pipeline: Source → Parser → Visitor → Context → Rules → Report."""

    def __init__(self):
        self.registry = AuditRegistry()
        self.registry.load_plugins('engine/rules')
        self.results: List[BestPracticeResult] = []
        self.errors: List[str] = []
        self.total_points = 0
        self.max_points = 0

    def audit(self, ast: ASTNode, code: str = "") -> Dict[str, Any]:
        """Jalankan semua rule terhadap AST dan kode."""
        from engine.best_practice_context import build_context
        ctx = build_context(ast, code)

        active_rules = self.registry.get_active_rules()
        cat_points: Dict[str, int] = {}
        max_per_cat = {
            'reliability': 25, 'memory': 20, 'performance': 15,
            'code_structure': 15, 'type_safety': 15, 'render': 10,
            'debug': 10, 'scope': 5, 'ux': 10, 'readability': 10
        }

        for rule in active_rules:
            start = time.perf_counter()
            try:
                passed = rule.check_fn(ctx)
                elapsed = (time.perf_counter() - start) * 1000
                evidence = ""
                if passed:
                    cat = rule.category
                    current = cat_points.get(cat, 0)
                    cap = max_per_cat.get(cat, 10)
                    if current + rule.points <= cap:
                        cat_points[cat] = current + rule.points
                        self.total_points += rule.points
                        evidence = self._find_evidence(rule, code)
                    else:
                        passed = False  # capped
                self.results.append(BestPracticeResult(rule, passed, evidence, elapsed))
            except Exception as e:
                self.errors.append(f"Rule {rule.id} ({rule.name}): {e}")

        return {
            'total_points': self.total_points,
            'passed_rules': sum(1 for r in self.results if r.passed),
            'total_rules': len(self.results),
            'categories': self.registry.list_categories(),
            'errors': self.errors
        }

    def _find_evidence(self, rule: AuditRule, code: str) -> str:
        import re
        patterns = {
            'barstate_guard': r'\bbarstate\.(isconfirmed|ishistory)\b',
            'na_guard': r'\bna\(',
            'nz_guard': r'\bnz\(',
            'nan_check': r'\bmath\.(is_nan|is_finite)\(',
            'array_eviction': r'\barray\.(shift|pop)\(',
            'matrix_eviction': r'\bmatrix\.remove_row\(',
            'drawing_limits': r'\bmax_(labels|lines|boxes)_count\s*=',
            'bars_back_limit': r'\bmax_bars_back\s*=',
            'force_overlay': r'\bforce_overlay\s*=\s*true\b',
            'hidden_plot': r'\bdisplay\s*=\s*display\.none\b',
            'logging': r'\blog\.(info|warning|error)\(',
            'export': r'\bexport\b',
            'typed_inputs': r'\binput\.(int|float|bool|color|source|price|time)\(',
        }
        pat = patterns.get(rule.name)
        if pat:
            for i, line in enumerate(code.split('\n'), 1):
                if re.search(pat, line):
                    return f"Line {i}: {line.strip()[:50]}"
        return "AST detection"

    def format_report(self) -> str:
        out = []
        out.append("┌" + "─" * 58 + "┐")
        out.append("│ 🏆 BEST PRACTICE (Plugin-based, ID-tracked)               │")
        out.append("├" + "─" * 58 + "┤")
        for r in self.results:
            if r.passed:
                icon = '✅'
                out.append(f"│ {icon} [{r.rule.id}] {r.rule.name:<25} +{r.rule.points:>2}p │")
                if r.evidence:
                    out.append(f"│    📍 {r.evidence[:50]:<50} │")
        out.append("├" + "─" * 58 + "┤")
        out.append(f"│ 💎 Total Points: {self.total_points:<3}  |  Rules passed: {sum(1 for r in self.results if r.passed)}/{len(self.results)}      │")
        out.append(f"│ 📊 Plugins: {len(self.registry.plugins)}  |  Errors: {len(self.errors)}                      │")
        out.append("└" + "─" * 58 + "┘")
        return '\n'.join(out)
