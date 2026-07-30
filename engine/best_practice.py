#!/usr/bin/env python3
"""Best Practice Orchestrator v3.5 — State reset, Evidence terintegrasi, config-based."""
import time, re
from typing import List, Dict, Any
from engine.parser import ASTNode
from engine.audit.registry import AuditRegistry, AuditRule
from engine.audit.context import AuditContext
from engine.audit.evidence import Evidence
from engine.audit.statistics import StatisticsVisitor
from engine.config import Severity, Grade, REPORT_WIDTH, MAX_POINTS_PER_CATEGORY

class BestPracticeResult:
    def __init__(self, rule: AuditRule, passed: bool, evidence: Evidence = None, execution_time_ms: float = 0):
        self.rule = rule; self.passed = passed; self.evidence = evidence; self.execution_time_ms = execution_time_ms

class BestPracticeOrchestrator:
    def __init__(self):
        self.registry = AuditRegistry()
        self.registry.load_plugins('engine/rules')
        self.results: List[BestPracticeResult] = []
        self.errors: List[str] = []
        self.total_points = 0

    def audit(self, ctx: AuditContext, code: str = "") -> Dict[str, Any]:
        # 🔴 RESET STATE setiap audit
        self.results.clear()
        self.errors.clear()
        self.total_points = 0

        active_rules = self.registry.get_active_rules()
        cat_points: Dict[str, int] = {}

        for rule in active_rules:
            start = time.perf_counter()
            try:
                passed = rule.check_fn(ctx)
                elapsed = (time.perf_counter() - start) * 1000
                evidence = None
                if passed:
                    cat = rule.category
                    current = cat_points.get(cat, 0)
                    cap = MAX_POINTS_PER_CATEGORY.get(cat, 10)
                    if current + rule.points <= cap:
                        cat_points[cat] = current + rule.points
                        self.total_points += rule.points
                        evidence = self._build_evidence(rule, code)
                    else:
                        passed = False
                self.results.append(BestPracticeResult(rule, passed, evidence, elapsed))
            except Exception as e:
                self.errors.append(f"{rule.id} {rule.name}: {e}")

        return {'total_points':self.total_points,'passed_rules':sum(1 for r in self.results if r.passed),'total_rules':len(self.results),'categories':self.registry.list_categories(),'errors':self.errors}

    def _build_evidence(self, rule: AuditRule, code: str) -> Evidence:
        patterns = {'barstate_guard':r'\bbarstate\.(isconfirmed|ishistory)\b','na_guard':r'\bna\(','nz_guard':r'\bnz\(','nan_check':r'\bmath\.(is_nan|is_finite)\(','array_eviction':r'\barray\.(shift|pop)\(','matrix_eviction':r'\bmatrix\.remove_row\(','drawing_limits':r'\bmax_(labels|lines|boxes)_count\s*=','bars_back_limit':r'\bmax_bars_back\s*=','force_overlay':r'\bforce_overlay\s*=\s*true\b','hidden_plot':r'\bdisplay\s*=\s*display\.none\b','logging':r'\blog\.(info|warning|error)\(','export':r'\bexport\b','typed_inputs':r'\binput\.(int|float|bool|color|source|price|time)\('}
        pat = patterns.get(rule.name)
        if pat:
            for i, line in enumerate(code.split('\n'), 1):
                if re.search(pat, line):
                    return Evidence(line=i, snippet=line.strip()[:80], confidence='MEDIUM', message=rule.description)
        return Evidence(snippet='AST detection', confidence='HIGH', message=rule.description)

    def format_report(self) -> str:
        W = REPORT_WIDTH
        out = []
        out.append("┌"+"─"*W+"┐")
        out.append(f"│ 🏆 BEST PRACTICE (State-safe, Evidence-backed)             │")
        out.append("├"+"─"*W+"┤")
        for r in self.results:
            if r.passed:
                out.append(f"│ ✅ [{r.rule.id}] {r.rule.name:<25} +{r.rule.points:>2}p │")
                if r.evidence:
                    out.append(f"│    📍 {r.evidence.to_line_string()[:50]:<50} │")
        out.append("├"+"─"*W+"┤")
        out.append(f"│ 💎 Total Points: {self.total_points:<3}  |  Rules passed: {sum(1 for r in self.results if r.passed)}/{len(self.results)}      │")
        out.append(f"│ 📊 Plugins: {len(self.registry.plugins)}  |  Errors: {len(self.errors)}                      │")
        out.append("└"+"─"*W+"┘")
        return '\n'.join(out)
