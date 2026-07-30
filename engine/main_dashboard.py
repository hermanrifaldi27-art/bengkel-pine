#!/usr/bin/env python3
"""
DASBOR UTAMA BENGKEL PINE — Informasi Lengkap, Profesional
"""
import os, sys, time
from engine.health_check import HealthCheck
from engine.config import ENGINE_VERSION, COLORS, DISCLAIMER, PASS_THRESHOLD, PUBLISH_THRESHOLD

class MainDashboard:
    @classmethod
    def show(cls, target_dir: str = "."):
        W = 58
        out = []
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        start_time = time.time()
        health = HealthCheck.check_all()
        pine_files = cls._find_pine_files(target_dir)

        # ═══════════ HEADER ═══════════
        out.append(f"╔{'═'*W}╗")
        out.append(f"║  🏠 DASBOR UTAMA BENGKEL PINE v{ENGINE_VERSION}                    ║")
        out.append(f"║  🕐 {now}                                         ║")
        out.append(f"╚{'═'*W}╝")
        out.append("")

        # ═══════════ RINGKASAN EKSEKUTIF ═══════════
        h_stat = health['overall_health']
        h_icon = '🟢' if 'HEALTHY' in h_stat else '🟡' if 'DEGRADED' in h_stat else '🔴'
        total_files = len(pine_files)
        total_size = sum(os.path.getsize(f) for f in pine_files if os.path.exists(f))
        
        # Analisis semua file
        all_reports = []
        total_issues = 0
        files_clean = 0
        files_warn = 0
        files_error = 0
        scores = []
        all_items = []
        file_scores = {}
        
        for f in pine_files:
            try:
                from engine.parser import PineAST
                from engine.extractor import extract_features
                from engine.scoring import ScoringEngine
                with open(f, 'r') as fh:
                    code = fh.read()
                ast = PineAST(code)
                features = extract_features(f) or []
                report = ScoringEngine.calculate(features, code, ast.root)
                all_reports.append((f, report))
                scores.append(report.total_score)
                file_scores[f] = report.total_score
                total_issues += len(report.items)
                if report.errors > 0: files_error += 1
                elif report.warnings > 0 or report.info > 0: files_warn += 1
                else: files_clean += 1
                for item in report.items:
                    all_items.append((f, item))
            except Exception as e:
                file_scores[f] = None

        elapsed = time.time() - start_time
        avg_score = sum(scores) / len(scores) if scores else 0
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 0
        min_file = next((f for f, s in file_scores.items() if s == min_score), "?")
        max_file = next((f for f, s in file_scores.items() if s == max_score and s is not None), "?")
        passed = sum(1 for s in scores if s >= PASS_THRESHOLD)
        publishable = sum(1 for s in scores if s >= PUBLISH_THRESHOLD)
        pass_pct = (passed / total_files * 100) if total_files > 0 else 0
        pub_pct = (publishable / total_files * 100) if total_files > 0 else 0

        out.append(f"┌{'─'*W}┐")
        out.append(f"│ {h_icon} SISTEM: {h_stat:<15} │ ⚡ Analisis {elapsed:.1f}s              │")
        out.append(f"│ 📂 {total_files} file Pine │ 📏 {total_size:,} bytes total            │")
        out.append(f"│ 📊 Skor rata²: {avg_score:.0f}/100 │ 🏆 Terbaik: {max_score} │ ⚠️ Terendah: {min_score} │")
        out.append(f"│ ✅ Lulus: {passed}/{total_files} ({pass_pct:.0f}%) │ 🚀 Siap Publikasi: {publishable}/{total_files} ({pub_pct:.0f}%) │")
        out.append(f"│ ❌ Error: {files_error} │ ⚠️ Warning: {files_warn} │ ✅ Bersih: {files_clean} │")
        out.append(f"│ 🔍 Total masalah: {total_issues} │ 📋 {len(all_items)} item │")
        out.append(f"└{'─'*W}┘")
        out.append("")

        # ═══════════ HISTOGRAM SKOR ═══════════
        if scores:
            out.append(f"┌{'─'*W}┐")
            out.append(f"│ 📊 DISTRIBUSI SKOR KODE                                 │")
            out.append(f"├{'─'*W}┤")
            dist = {r: 0 for r in [(90,100), (75,89), (60,74), (40,59), (0,39)]}
            labels = ['A (90-100)', 'B (75-89)', 'C (60-74)', 'D (40-59)', 'E (0-39)']
            for s in scores:
                for (lo, hi), _ in dist.items():
                    if lo <= s <= hi:
                        dist[(lo, hi)] += 1
                        break
            max_count = max(dist.values()) if dist else 1
            for (lo, hi), label in zip(dist.keys(), labels):
                count = dist[(lo, hi)]
                bar_len = int(count / max_count * 30) if max_count > 0 else 0
                bar = '█' * bar_len + '░' * (30 - bar_len)
                pct = (count / total_files * 100) if total_files > 0 else 0
                out.append(f"│ {label:<12} {bar} {count:>3} ({pct:.0f}%) │")
            out.append(f"└{'─'*W}┘")
            out.append("")

        # ═══════════ FILE TERBURUK & TERBAIK ═══════════
        if total_files >= 2:
            out.append(f"┌{'─'*W}┐")
            out.append(f"│ ⚠️ PERLU PERHATIAN (Skor Terendah)                        │")
            out.append(f"├{'─'*W}┤")
            for f, report in all_reports:
                if report.total_score == min_score:
                    fn = os.path.basename(f)
                    out.append(f"│ 📄 {fn[:50]:<50} │")
                    out.append(f"│    Skor: {report.total_score}/100 Grade: {report.grade.value[0]} │")
                    for item in report.items[:3]:
                        icon = COLORS.get(item.severity.value.upper(), '❓')
                        out.append(f"│    {icon} {item.message[:48]:<48} │")
            out.append(f"├{'─'*W}┤")
            out.append(f"│ 🏆 TERBAIK (Skor Tertinggi)                                │")
            out.append(f"├{'─'*W}┤")
            for f, report in all_reports:
                if report.total_score == max_score and report.total_score >= 90:
                    fn = os.path.basename(f)
                    out.append(f"│ 📄 {fn[:50]:<50} │")
                    out.append(f"│    Skor: {report.total_score}/100 Grade: {report.grade.value[0]} │")
            out.append(f"└{'─'*W}┘")
            out.append("")

        # ═══════════ TABEL SEMUA FILE ═══════════
        if pine_files:
            out.append(f"┌{'─'*W}┐")
            out.append(f"│ 📁 SEMUA FILE PINE ({total_files})                              │")
            out.append(f"├{'─'*W}┤")
            out.append(f"│ {'FILE':<25} {'SKOR':>5} {'GRD':>3} {'ERR':>3} {'WRN':>3} {'INF':>3} │")
            out.append(f"├{'─'*W}┤")
            for f in pine_files:
                fn = os.path.basename(f)[:23]
                if f in file_scores and file_scores[f] is not None:
                    for fr, report in all_reports:
                        if fr == f:
                            skor = report.total_score
                            grd = report.grade.value[0]
                            bar = cls._mini_bar(skor)
                            out.append(f"│ {fn:<23} {skor:>3} {bar} {grd}  {report.errors:>2}  {report.warnings:>2}  {report.info:>2} │")
                            break
                else:
                    out.append(f"│ {fn:<23} ERR ───────   ?   ?   ? │")
            out.append(f"└{'─'*W}┘")
            out.append("")

        # ═══════════ SEMUA MASALAH ═══════════
        if all_items:
            # Kelompokkan berdasarkan kategori
            from collections import Counter
            cat_counts = Counter(item.category for _, item in all_items)
            out.append(f"┌{'─'*W}┐")
            out.append(f"│ 🔍 {len(all_items)} MASALAH TERDETEKSI — Berdasarkan Kategori       │")
            out.append(f"├{'─'*W}┤")
            for cat, count in cat_counts.most_common(5):
                risk = ""
                try:
                    from engine.config import CATEGORY_RISK
                    risk = CATEGORY_RISK.get(cat, "")
                except: pass
                icon = COLORS.get(cat.upper(), '❓')
                out.append(f"│ {icon} {cat:<20} {count:>3} masalah │")
                if risk:
                    out.append(f"│    Risiko: {risk[:48]:<48} │")
            out.append(f"├{'─'*W}┤")
            out.append(f"│ 📋 Daftar Lengkap ({len(all_items)} item):                      │")
            out.append(f"├{'─'*W}┤")
            for f, item in all_items[:20]:  # Maks 20 item
                icon = COLORS.get(item.severity.value.upper(), '❓')
                fn = os.path.basename(f)[:12]
                msg = item.message[:40]
                line = f"L{item.line}" if item.line else ""
                out.append(f"│ {icon} {fn:<12} {msg:<38} {line:>6} │")
            if len(all_items) > 20:
                out.append(f"│ ... dan {len(all_items)-20} masalah lainnya                        │")
            out.append(f"└{'─'*W}┘")
            out.append("")

        # ═══════════ TINDAKAN CEPAT ═══════════
        out.append(f"┌{'─'*W}┐")
        out.append(f"│ ⚡ TINDAKAN CEPAT                                        │")
        out.append(f"├{'─'*W}┤")
        out.append(f"│ 🖥️  dashboard <file>  → Analisis lengkap 1 file      │")
        out.append(f"│ 📊 score <file>      → Skor & grade saja             │")
        out.append(f"│ 🏥 health            → Cek kesehatan sistem          │")
        out.append(f"│ 🔧 repair <file>     → Perbaiki otomatis             │")
        out.append(f"│ 📋 lint <file>       → Lint file .pine               │")
        out.append(f"└{'─'*W}┘")
        out.append("")

        # ═══════════ FOOTER ═══════════
        out.append(f"⚠️  {DISCLAIMER}")
        out.append(f"   Skor ≥{PASS_THRESHOLD} = Lulus │ Skor ≥{PUBLISH_THRESHOLD} = Siap Publikasi")

        return '\n'.join(out)

    @classmethod
    def _mini_bar(cls, score: int) -> str:
        filled = score // 10
        return f"{'█'*filled}{'░'*(10-filled)}"

    @classmethod
    def _find_pine_files(cls, directory: str) -> list:
        pine_files = []
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.') and 'backup' not in d.lower()]
            for file in files:
                if file.endswith('.pine'):
                    pine_files.append(os.path.join(root, file))
        return sorted(pine_files)[:20]
