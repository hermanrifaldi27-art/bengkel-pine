#!/usr/bin/env python3
"""
Auto-Fixer — Perbaikan otomatis dengan diff & konfirmasi
"""
import difflib
import os
import shutil
from typing import List, Optional, Tuple
from engine.config import COLORS

class AutoFixer:
    """Perbaiki kode Pine berdasarkan masalah yang terdeteksi."""

    @classmethod
    def fix(cls, file_path: str, features: List, code: str, dry_run: bool = True, auto_confirm: bool = False) -> Optional[str]:
        """
        Terapkan perbaikan ke kode sumber.
        
        Args:
            file_path: Path file asli
            features: Daftar masalah yang terdeteksi
            code: Kode sumber asli
            dry_run: Jika True, hanya tampilkan diff tanpa menulis
            auto_confirm: Jika True, langsung setujui semua perbaikan
        
        Returns:
            Kode yang sudah diperbaiki, atau None jika tidak ada perubahan
        """
        fixes = []
        for feature in features:
            fix = cls._generate_fix(feature, code)
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
            elif fix['type'] == 'insert_before':
                idx = patched.find(fix['anchor'])
                if idx >= 0:
                    patched = patched[:idx] + fix['new'] + '\n' + patched[idx:]

        if patched == code:
            return None

        # Tampilkan diff
        diff = cls._generate_diff(code, patched, file_path)
        print(diff)

        if dry_run:
            print(f"\n  {COLORS.get('INFO', 'ℹ️')} DRY-RUN: File tidak diubah.")
            print(f"  Gunakan --apply untuk menerapkan perbaikan.")
            return patched

        # Konfirmasi
        if not auto_confirm:
            print(f"\n  ⚠️  Perubahan di atas akan diterapkan ke file.")
            response = input(f"  Lanjutkan? [y/N]: ").strip().lower()
            if response != 'y':
                print(f"  ❌ Dibatalkan.")
                return None

        # Backup
        backup_path = file_path + '.bak'
        shutil.copy2(file_path, backup_path)
        print(f"  📦 Backup disimpan ke {backup_path}")

        # Tulis
        with open(file_path, 'w') as f:
            f.write(patched)
        print(f"  ✅ Perbaikan diterapkan ke {file_path}")

        return patched

    @classmethod
    def _generate_fix(cls, feature, code: str) -> Optional[dict]:
        """Hasilkan perbaikan berdasarkan tipe masalah."""
        detector_id = feature.detector_id
        anchor = feature.anchor if feature.anchor else ""
        tactic = feature.tactic if feature.tactic else ""

        if 'request_security_lookahead' in detector_id:
            # Cari request.security( yang tidak punya lookahead
            import re
            pattern = r'(request\.security\([^)]*?)\)'
            matches = list(re.finditer(pattern, code))
            for m in matches:
                call = m.group(1)
                if 'lookahead' not in call:
                    new_call = call.rstrip(')') + ', lookahead = barmerge.lookahead_off)'
                    return {
                        'type': 'replace',
                        'old': m.group(1),
                        'new': new_call,
                        'description': 'Tambahkan lookahead = barmerge.lookahead_off'
                    }

        elif 'plot_in_if' in detector_id or 'obj_in_if' in detector_id:
            # Ambil nama fungsi dari anchor
            func_name = anchor.split('(')[0] if '(' in anchor else ''
            if func_name:
                # Generate deklarasi var di luar if
                var_name = func_name.split('.')[-1] if '.' in func_name else func_name
                decl = f'var {var_name}_var = {func_name}.new()\n'
                return {
                    'type': 'insert_before',
                    'anchor': 'if ',
                    'new': decl,
                    'description': f'Deklarasikan var {var_name}_var di luar if'
                }

        elif 'var_int_na' in detector_id:
            return {
                'type': 'replace',
                'old': '= na',
                'new': '= 0',
                'description': 'Ganti na dengan 0'
            }

        elif 'array_unbounded' in detector_id:
            arr_name = anchor.replace('array.push(', '').replace(')', '').strip()
            eviction = f'while array.size({arr_name}) > 100\n    array.shift({arr_name})'
            return {
                'type': 'insert_after',
                'anchor': anchor,
                'new': eviction,
                'description': f'Tambahkan eviction untuk array {arr_name}'
            }

        elif 'matrix_unbounded' in detector_id:
            mat_name = anchor.replace('matrix.add_row(', '').replace(')', '').strip()
            eviction = f'if matrix.rows({mat_name}) > 100\n    matrix.remove_row({mat_name}, matrix.rows({mat_name}) - 1)'
            return {
                'type': 'insert_after',
                'anchor': anchor,
                'new': eviction,
                'description': f'Tambahkan eviction untuk matrix {mat_name}'
            }

        elif 'alertcondition_in_if' in detector_id:
            return {
                'type': 'replace',
                'old': 'alertcondition(',
                'new': '// Pindahkan ke global scope:\n// alertcondition(',
                'description': 'Komentari alertcondition di dalam if'
            }

        return None

    @classmethod
    def _generate_diff(cls, original: str, patched: str, file_path: str) -> str:
        """Hasilkan unified diff."""
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile=f'a/{file_path}',
            tofile=f'b/{file_path}',
        )
        return ''.join(diff)
