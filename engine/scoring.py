#!/usr/bin/env python3
"""Pine Script Scoring Engine v2.1 — Konteks dari Feature, metrik akurat."""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from engine.config import *
from engine.config import COLORS as C

@dataclass
class ScoreItem:
    category: str; message: str; severity: Severity
    line: Optional[int] = None; col: Optional[int] = None
    deduction: int = 0; multiplier: float = 1.0
    context: str = ""; risk: str = ""; fix_suggestion: Optional[str] = None

@dataclass
class ScoreReport:
    total_score: int = 100; grade: Grade = Grade.A
    items: List[ScoreItem] = field(default_factory=list)
    errors: int = 0; warnings: int = 0; info: int = 0; hints: int = 0
    pine_version: int = PINE_DEFAULT_VERSION
    code_metrics: Dict[str, Any] = field(default_factory=dict)
    passed: bool = True; ready_to_publish: bool = False
    calculation_detail: List[str] = field(default_factory=list)

class ScoringEngine:

    @classmethod
    def calculate(cls, features: List[Any], code: str = "", ast: Any = None) -> ScoreReport:
        report = ScoreReport()
        report.pine_version = cls._detect_pine_version(code)

        if not features:
            report.total_score = 100; report.grade = Grade.A
            report.passed = True; report.ready_to_publish = True
            report.calculation_detail.append("✅ Tidak ada masalah — skor 100/100")
            report.code_metrics = cls._calculate_metrics(code, ast)
            return report

        category_deductions: Dict[str, int] = {}

        for feature in features:
            category = feature.module
            base = BASE_DEDUCTION.get(category, 5)

            # ✅ AMBIL KONTEKS DARI ATRIBUT FEATURE, BUKAN PARSING ANCHOR
            context = getattr(feature, 'context', 'is_indicator')
            if not context or context == 'is_indicator':
                # Fallback: cek dari anchor string
                anchor_str = str(feature.anchor) if feature.anchor else ""
                if 'loop' in anchor_str.lower() or 'for ' in anchor_str.lower() or 'while ' in anchor_str.lower():
                    context = 'in_loop'
                elif 'if ' in anchor_str.lower() or 'if_' in anchor_str.lower():
                    context = 'in_if'
                elif 'function' in anchor_str.lower() or 'func' in anchor_str.lower():
                    context = 'in_function'
                elif 'strategy' in code.lower():
                    context = 'is_strategy'

            multiplier = CONTEXT_MULTIPLIERS.get(context, 1.0)
            if report.pine_version == 5:
                multiplier *= 1.1
            deduction = int(base * multiplier)

            # Batasi per kategori
            current_cat = category_deductions.get(category, 0)
            remaining = MAX_DEDUCTION_PER_CATEGORY - current_cat
            actual_deduction = min(deduction, remaining)
            category_deductions[category] = current_cat + actual_deduction

            severity = CATEGORY_SEVERITY.get(category, Severity.HINT)
            risk = CATEGORY_RISK.get(category, "")

            line = None
            if feature.anchor:
                parts = str(feature.anchor).replace('line ', '').split(':')
                if len(parts) >= 2:
                    try: line = int(parts[0])
                    except: pass

            item = ScoreItem(category=category, message=feature.goal, severity=severity,
                             line=line, deduction=actual_deduction, multiplier=multiplier,
                             context=context, risk=risk,
                             fix_suggestion=feature.tactic if feature.tactic else None)
            report.items.append(item)

            if severity == Severity.ERROR: report.errors += 1
            elif severity == Severity.WARNING: report.warnings += 1
            elif severity == Severity.INFO: report.info += 1
            else: report.hints += 1

            report.total_score -= actual_deduction

            note = f" (dibatasi dari {deduction})" if actual_deduction < deduction else ""
            report.calculation_detail.append(
                f"-{actual_deduction} [{category}] {feature.goal[:35]} "
                f"(base={base}, ctx={context}, ×{multiplier}{note})"
            )

        report.total_score = max(0, min(100, report.total_score))
        for grade in Grade:
            low, high = grade.value[1], grade.value[2]
            if low <= report.total_score <= high:
                report.grade = grade; break

        report.passed = report.total_score >= PASS_THRESHOLD
        report.ready_to_publish = report.total_score >= PUBLISH_THRESHOLD
        report.code_metrics = cls._calculate_metrics(code, ast)
        return report

    @classmethod
    def _detect_pine_version(cls, code: str) -> int:
        import re
        m = re.search(r'//@version\s*=\s*(\d+)', code)
        return int(m.group(1)) if m else PINE_DEFAULT_VERSION

    @classmethod
    def _calculate_metrics(cls, code: str, ast: Any = None) -> Dict[str, Any]:
        lines = code.split('\n') if code else []
        non_empty = [l for l in lines if l.strip() and not l.strip().startswith('//')]
        metrics = {'total_lines': len(lines), 'code_lines': len(non_empty),
                   'functions': 0, 'variables': 0, 'types': 0}
        if ast:
            try:
                # ✅ PERBAIKI: hitung langsung dari AST body
                from engine.parser import FunctionDeclaration, MethodDeclaration, VarDeclaration, TypeDeclaration
                def count_nodes(node, counters):
                    if isinstance(node, (FunctionDeclaration, MethodDeclaration)):
                        counters['functions'] += 1
                    elif isinstance(node, VarDeclaration):
                        counters['variables'] += 1
                    elif isinstance(node, TypeDeclaration):
                        counters['types'] += 1
                    if hasattr(node, 'body'):
                        for child in node.body:
                            count_nodes(child, counters)
                    # Module body
                    if hasattr(node, 'children'):
                        pass
                # Hitung dari modul
                for stmt in ast.body:
                    if isinstance(stmt, (FunctionDeclaration, MethodDeclaration)):
                        metrics['functions'] += 1
                    elif isinstance(stmt, VarDeclaration):
                        metrics['variables'] += 1
                    elif isinstance(stmt, TypeDeclaration):
                        metrics['types'] += 1
            except:
                pass
        return metrics

    @classmethod
    def format_report(cls, report: ScoreReport) -> str:
        W = 58
        grd = report.grade.value[0]
        out = []
        out.append("╔" + "═" * W + "╗")
        out.append(f"║  {C[grd]} SKOR: {report.total_score:3}/100   GRADE: {grd}   Pine v{report.pine_version}     ║")
        out.append(f"║  {report.grade.value[3][:W-4]:<{W-4}} ║")
        out.append("╠" + "═" * W + "╣")
        status_icon = C['PASS'] if report.passed else C['FAIL']
        pub_icon = C['PASS'] if report.ready_to_publish else '⚠️'
        out.append(f"║  {status_icon} Lulus ≥{PASS_THRESHOLD}  |  {pub_icon} Publikasi ≥{PUBLISH_THRESHOLD}                 ║")
        out.append(f"║  ❌{report.errors} ⚠️{report.warnings} ℹ️{report.info} 💡{report.hints}   |  Baris:{report.code_metrics.get('total_lines',0)} Kode:{report.code_metrics.get('code_lines',0)} Fn:{report.code_metrics.get('functions',0)} Var:{report.code_metrics.get('variables',0)} ║")
        if report.calculation_detail:
            out.append("╠" + "═" * W + "╣")
            out.append("║  📋 Rincian Pengurangan:                                     ║")
            for d in report.calculation_detail[:5]:
                out.append(f"║  {d[:W-4]:<{W-4}} ║")
        out.append("╠" + "═" * W + "╣")
        out.append(f"║  ⚠️ {DISCLAIMER[:W-6]:<{W-6}} ║")
        out.append("╚" + "═" * W + "╝")
        return '\n'.join(out)
