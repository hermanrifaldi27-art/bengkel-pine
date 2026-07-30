#!/usr/bin/env python3
"""Dashboard Generator v2.1 — Rapi di HP, skor sekali hitung, masalah lengkap."""
import os
from engine.scoring import ScoringEngine, ScoreReport
from engine.health_check import HealthCheck
from engine.config import COLORS, ENGINE_VERSION, DISCLAIMER

class Dashboard:

    @classmethod
    def generate(cls, file_path: str, code: str = "", features: list = None, ast=None) -> str:
        W = 58
        fn = os.path.basename(file_path)
        sz = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        out = []

        # ── HEADER ──
        out.append("╔" + "═" * W + "╗")
        out.append(f"║  📊 BENGKEL PINE v{ENGINE_VERSION} — Analisis Kode          ║")
        out.append(f"║  📁 {fn[:W-6]:<{W-6}} ║")
        out.append(f"║  📏 {sz:,} bytes                                           ║")
        out.append("╚" + "═" * W + "╝")
        out.append("")

        # ── DISCLAIMER ──
        out.append(f"⚠️  {DISCLAIMER}")
        out.append("")

        # ── SKOR (HITUNG SEKALI) ──
        report = None
        if features is not None:
            report = ScoringEngine.calculate(features, code, ast)
            grd = report.grade.value[0]
            out.append(cls._score_bar(report.total_score, grd))
            out.append(f"  Grade: {grd} — {report.grade.value[3]}")
            out.append(f"  ❌{report.errors} ⚠️{report.warnings} ℹ️{report.info} 💡{report.hints}")
            out.append("")

            # Status
            if report.passed:
                out.append(f"  {COLORS['PASS']} LULUS (≥75)")
                if report.ready_to_publish:
                    out.append(f"  {COLORS['PASS']} SIAP PUBLIKASI (≥90)")
                else:
                    out.append("  ⚠️  Perlu perbaikan kecil untuk publikasi")
            else:
                out.append(f"  {COLORS['FAIL']} PERLU PERBAIKAN (≥75)")
            out.append("")

            # ── RINCIAN ──
            if report.calculation_detail:
                out.append("┌" + "─" * 56 + "┐")
                out.append("│ 📋 Rincian Pengurangan                                      │")
                out.append("├" + "─" * 56 + "┤")
                for d in report.calculation_detail[:5]:
                    out.append(f"│ {d[:54]:<54} │")
                out.append("└" + "─" * 56 + "┘")
                out.append("")

            # ── DAFTAR MASALAH ──
            if report.items:
                out.append("┌" + "─" * 56 + "┐")
                out.append("│ 📋 Daftar Masalah                                            │")
                out.append("├─┬────────┬──────────────────────────────────────────────────┤")
                for i, it in enumerate(report.items, 1):
                    ico = COLORS.get(it.severity.value.upper(), '❓')
                    msg = it.message[:36]
                    out.append(f"│{i:<2}│{ico:<6}  │ {msg:<36} │")
                    if it.risk:
                        out.append(f"│  │        │ Risiko: {it.risk[:32]:<32} │")
                    if it.line:
                        out.append(f"│  │        │ 📍 Baris {it.line:<30} │")
                    if it.fix_suggestion:
                        s = it.fix_suggestion[:32]
                        out.append(f"│  │        │ 💡 {s:<32} │")
                out.append("└─┴────────┴──────────────────────────────────────────────────┘")
                out.append("")

        # ── METRIK ──
        if report:
            m = report.code_metrics
            out.append("┌" + "─" * 30 + "┐")
            out.append("│ 📊 Metrik Kode                  │")
            out.append(f"│ Baris total: {m.get('total_lines',0):<5}             │")
            out.append(f"│ Baris kode:  {m.get('code_lines',0):<5}             │")
            out.append(f"│ Fungsi:      {m.get('functions',0):<5}             │")
            out.append(f"│ Variabel:    {m.get('variables',0):<5}             │")
            out.append(f"│ Tipe:        {m.get('types',0):<5}             │")
            out.append("└" + "─" * 30 + "┘")
            out.append("")

        # ── KESEHATAN SISTEM ──
        h = HealthCheck.check_all()
        hic = COLORS.get(h['overall_health'].split()[0], '❓')
        out.append("┌" + "─" * 30 + "┐")
        out.append(f"│ 🏥 Sistem: {hic} {h['overall_health']:<15} │")
        out.append(f"│ Parser:  {h['parser'].get('status','?'):<10} │")
        out.append(f"│ Semantik:{h['semantic'].get('status','?'):<10} │")
        out.append(f"│ Ekstrak: {h['extractor'].get('status','?'):<10} │")
        out.append(f"│ Builtin: {h['builtins'].get('namespaces',0):<3} namespace    │")
        out.append("└" + "─" * 30 + "┘")

        return '\n'.join(out)

    @classmethod
    def _score_bar(cls, score: int, grade: str) -> str:
        filled = score // 5
        bar = COLORS['BAR_FILL'] * filled + COLORS['BAR_EMPTY'] * (20 - filled)
        return f"  {COLORS[grade]} [{bar}] {score}/100"
