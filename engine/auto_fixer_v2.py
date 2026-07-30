#!/usr/bin/env python3
"""
Auto-Fixer v2.0 — Perbaikan otomatis dengan diff viewer, backup, dan knowledge base.
"""
import difflib, os, shutil
from typing import List, Optional, Dict, Any
from engine.unified_auditor import UnifiedFinding, UnifiedReport
from engine.knowledge_base import KnowledgeBase

class AutoFixerV2:
    """Auto-Fixer yang menggunakan Knowledge Base untuk perbaikan cerdas."""

    def __init__(self):
        self.kb = KnowledgeBase()

    def fix(self, file_path: str, report: UnifiedReport, code: str,
            dry_run: bool = True, auto_confirm: bool = False) -> Optional[str]:
        """
        Terapkan perbaikan otomatis dengan diff viewer.
        Returns: kode yang sudah diperbaiki, atau None jika tidak ada perubahan.
        """
        fixes = []
        for finding in report.findings:
            if finding.source == 'extractor':
                fix = self._generate_fix(finding, code)
                if fix:
                    fixes.append(fix)

        if not fixes:
            return None

        # Terapkan semua perbaikan
        patched = code
        for fix in fixes:
            if fix['type'] == 'replace':
                patched = patched.replace(fix['old'], fix['new'], 1)
            elif fix['type'] == 'insert_after':
                idx = patched.find(fix['anchor'])
                if idx >= 0:
                    end_idx = patched.find('\n', idx)
                    if end_idx >= 0:
                        patched = patched[:end_idx+1] + fix['new'] + '\n' + patched[end_idx+1:]

        if patched == code:
            return None

        # Diff
        diff = self._generate_diff(code, patched, file_path)
        print(diff)

        if dry_run:
            print(f"\n  DRY-RUN: File tidak diubah.")
            print(f"  Gunakan --apply untuk menerapkan perbaikan.")
            return patched

        if not auto_confirm:
            response = input(f"\n  Lanjutkan? [y/N]: ").strip().lower()
            if response != 'y':
                print(f"  Dibatalkan.")
                return None

        # Backup
        backup_path = file_path + '.bak'
        shutil.copy2(file_path, backup_path)
        print(f"  Backup: {backup_path}")

        # Tulis
        with open(file_path, 'w') as f:
            f.write(patched)
        print(f"  Perbaikan diterapkan ke {file_path}")

        return patched

    def _generate_fix(self, finding: UnifiedFinding, code: str) -> Optional[dict]:
        """Hasilkan perbaikan dari finding + knowledge base."""
        # Cek knowledge base dulu
        kb_fix = self.kb.get_fix_for(finding.detector_id)
        if kb_fix:
            return {'type': 'insert_after', 'anchor': finding.detector_id, 'new': kb_fix, 'description': 'KB fix'}

        # Fallback: perbaikan sederhana berdasarkan detector_id
        if 'request_security' in finding.detector_id:
            import re
            pattern = r'(request\.security\([^)]*?)\)'
            for m in re.finditer(pattern, code):
                call = m.group(1)
                if 'lookahead' not in call:
                    new_call = call.rstrip(')') + ', lookahead = barmerge.lookahead_off, gaps = barmerge.gaps_off)'
                    return {'type': 'replace', 'old': m.group(1), 'new': new_call, 'description': 'Tambahkan lookahead & gaps'}

        if 'obj_in_if' in finding.detector_id or 'drawing_in_loop' in finding.detector_id:
            return {'type': 'replace', 'old': finding.detector_id, 'new': '// FIX: Pindahkan ke deklarasi var di luar if/loop', 'description': 'Komentari untuk perbaikan manual'}

        return None

    def _generate_diff(self, original: str, patched: str, file_path: str) -> str:
        return ''.join(difflib.unified_diff(
            original.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile=f'a/{file_path}',
            tofile=f'b/{file_path}',
        ))
