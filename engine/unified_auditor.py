#!/usr/bin/env python3
"""
Unified Auditor v1.0 — Satu pipeline terpadu: Extractor (masalah) + Plugin (best practice)
"""
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from engine.parser import PineAST
from engine.extractor import FeatureExtractor
from engine.audit.registry import AuditRegistry
from engine.audit.context import AuditContext
from engine.audit.evidence import Evidence
from engine.config import Severity, Grade, MAX_POINTS_PER_CATEGORY, REPORT_WIDTH

@dataclass
class UnifiedFinding:
    """Satu temuan dari pipeline terpadu."""
    source: str          # 'extractor' atau 'plugin'
    category: str
    message: str
    severity: Severity
    points: int = 0       # positif = best practice, negatif = masalah
    evidence: Optional[Evidence] = None
    detector_id: str = ""
    diag_code: str = ""

@dataclass
class UnifiedReport:
    """Laporan terpadu dari Extractor + Plugin System."""
    file_path: str = ""
    total_score: int = 100
    grade: Grade = Grade.A
    errors: int = 0
    warnings: int = 0
    info: int = 0
    hints: int = 0
    findings: List[UnifiedFinding] = field(default_factory=list)
    extraction_count: int = 0      # jumlah masalah dari Extractor
    best_practice_points: int = 0  # total poin dari Plugin
    best_practice_count: int = 0   # jumlah best practice yang lulus
    plugins_loaded: int = 0
    rules_total: int = 0
    errors_loading: int = 0

class UnifiedAuditor:
    """Auditor terpadu: menjalankan Extractor + Plugin System dalam satu pipeline."""

    def __init__(self):
        self.registry = AuditRegistry()
        self.registry.load_plugins('engine/rules')

    def audit(self, ast_root: Any, code: str, file_path: str = "") -> UnifiedReport:
        """Jalankan audit terpadu pada satu file."""
        report = UnifiedReport(file_path=file_path)
        start_time = time.perf_counter()

        # ── 1. Jalankan Extractor ──
        try:
            extractor = FeatureExtractor(ast_root, code)
            features = extractor.extract_all()
            report.extraction_count = len(features)

            for f in features:
                # Tentukan severity dari detektor
                sev = self._map_detector_severity(f.detector_id)
                finding = UnifiedFinding(
                    source='extractor',
                    category=f.module,
                    message=f.goal,
                    severity=sev,
                    points=-self._deduction_for(f.detector_id),  # negatif = pengurangan
                    detector_id=f.detector_id,
                    diag_code=getattr(f, 'diagnostic', None)
                )
                report.findings.append(finding)

                # Update counter severity
                if sev == Severity.ERROR: report.errors += 1
                elif sev == Severity.WARNING: report.warnings += 1
                elif sev == Severity.INFO: report.info += 1
                else: report.hints += 1

        except Exception as e:
            report.errors_loading += 1

        # ── 2. Jalankan Plugin System ──
        try:
            from engine.best_practice_context import build_context
            ctx = build_context(ast_root, code)
            active_rules = self.registry.get_active_rules()
            report.plugins_loaded = len(self.registry.plugins)
            report.rules_total = len(active_rules)

            cat_points: Dict[str, int] = {}
            for rule in active_rules:
                try:
                    passed = rule.check_fn(ctx)
                    if passed:
                        cat = rule.category
                        current = cat_points.get(cat, 0)
                        cap = MAX_POINTS_PER_CATEGORY.get(cat, 10)
                        if current + rule.points <= cap:
                            cat_points[cat] = current + rule.points
                            report.best_practice_points += rule.points
                            report.best_practice_count += 1

                            # Evidence
                            evidence = self._build_evidence(rule, code)
                            finding = UnifiedFinding(
                                source='plugin',
                                category=rule.category,
                                message=rule.description,
                                severity=rule.severity,
                                points=rule.points,
                                evidence=evidence,
                                detector_id=rule.id
                            )
                            report.findings.append(finding)
                except Exception:
                    pass

        except Exception as e:
            report.errors_loading += 1

        # ── 3. Hitung skor akhir ──
        deductions = sum(abs(f.points) for f in report.findings if f.points < 0)
        bonus = sum(f.points for f in report.findings if f.points > 0)
        report.total_score = max(0, min(100, 100 - deductions + bonus // 5))  # bonus dibagi 5 agar tidak terlalu dominan

        for grade in Grade:
            low, high = grade.value[1], grade.value[2]
            if low <= report.total_score <= high:
                report.grade = grade
                break

        return report

    def _map_detector_severity(self, detector_id: str) -> Severity:
        """Petakan detector_id ke severity."""
        error_detectors = {'request_security_lookahead_v1', 'security_in_loop_v1', 'lookahead_bias_v1', 'security_gaps_v1'}
        warning_detectors = {'plot_in_if_v1', 'hline_in_if_v1', 'redundant_plot_v1', 'input_type_mismatch_v1',
                            'array_unbounded_v1', 'matrix_unbounded_v1', 'alertcondition_in_if_v1',
                            'drawing_in_loop_v1', 'rebuild_in_islast_v1'}
        info_detectors = {'obj_in_if_v1', 'var_int_na_v1', 'unused_variable_v1', 'magic_number_v1'}

        if detector_id in error_detectors: return Severity.ERROR
        if detector_id in warning_detectors: return Severity.WARNING
        if detector_id in info_detectors: return Severity.INFO
        return Severity.HINT

    def _deduction_for(self, detector_id: str) -> int:
        """Pengurangan skor berdasarkan detector_id."""
        deductions = {
            'request_security_lookahead_v1': 10, 'security_in_loop_v1': 12, 'lookahead_bias_v1': 10,
            'security_gaps_v1': 8, 'plot_in_if_v1': 8, 'hline_in_if_v1': 8, 'redundant_plot_v1': 5,
            'input_type_mismatch_v1': 5, 'array_unbounded_v1': 8, 'matrix_unbounded_v1': 8,
            'alertcondition_in_if_v1': 8, 'obj_in_if_v1': 5, 'var_int_na_v1': 3,
            'drawing_in_loop_v1': 5, 'rebuild_in_islast_v1': 5, 'unused_variable_v1': 3,
            'magic_number_v1': 3
        }
        return deductions.get(detector_id, 5)

    def _build_evidence(self, rule: Any, code: str) -> Optional[Evidence]:
        """Bangun evidence untuk rule plugin."""
        import re
        patterns = {
            'barstate_guard': r'\bbarstate\.(isconfirmed|ishistory)\b',
            'na_guard': r'\bna\(', 'nz_guard': r'\bnz\(',
            'force_overlay': r'\b(force_overlay|overlay)\s*=\s*true\b',
            'hidden_plot': r'\bdisplay\s*=\s*display\.none\b',
            'drawing_limits': r'\bmax_(labels|lines|boxes)_count\s*=',
        }
        pat = patterns.get(rule.name)
        if pat:
            for i, line in enumerate(code.split('\n'), 1):
                if re.search(pat, line):
                    return Evidence(line=i, snippet=line.strip()[:80], confidence='MEDIUM', message=rule.description)
        return Evidence(snippet='AST detection', confidence='HIGH', message=rule.description)

    def format_report(self, report: UnifiedReport) -> str:
        """Format laporan terpadu."""
        W = REPORT_WIDTH
        out = []
        out.append("╔" + "═" * W + "╗")
        out.append(f"║  📊 UNIFIED AUDIT: {report.file_path[:45]:<45} ║")
        out.append(f"║  🟢 SKOR: {report.total_score:>3}/100  GRADE: {report.grade.value[0]}  Pine v6     ║")
        out.append(f"║  {report.grade.value[3][:W-4]:<{W-4}} ║")
        out.append("╠" + "═" * W + "╣")
        out.append(f"║  🔍 Extractor: {report.extraction_count} masalah │ 🏆 Plugin: {report.best_practice_count}/{report.rules_total} rules │ +{report.best_practice_points} pts ║")
        out.append(f"║  ❌{report.errors} ⚠️{report.warnings} ℹ️{report.info} 💡{report.hints}   │  Plugins: {report.plugins_loaded} │ Errors: {report.errors_loading} ║")
        out.append("╠" + "═" * W + "╣")

        if report.findings:
            out.append(f"║  📋 TEMUAN ({len(report.findings)}):                                     ║")
            for f in report.findings[:10]:
                icon = '❌' if f.severity == Severity.ERROR else '⚠️' if f.severity == Severity.WARNING else 'ℹ️' if f.severity == Severity.INFO else '💡'
                pts = f"{'+' if f.points > 0 else ''}{f.points}p"
                src = '🔍' if f.source == 'extractor' else '🏆'
                out.append(f"║  {icon} {src} [{f.category[:12]:<12}] {f.message[:35]:<35} {pts:>5} ║")

        out.append("╚" + "═" * W + "╝")
        return '\n'.join(out)
