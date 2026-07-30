#!/usr/bin/env python3
"""
Auto-Fixer v3.0 — Multi-pass fix, confidence threshold, rollback, engineer-grade.
"""
import difflib, os, shutil
from typing import List, Optional, Dict, Any, Tuple
from engine.knowledge_base_proactive import ProactiveKnowledgeBase

class AutoFixerV3:
    """Auto-Fixer engineer-grade: multi-pass, confidence-gated, rollback-safe."""

    def __init__(self, kb: Optional[ProactiveKnowledgeBase] = None):
        self.kb = kb or ProactiveKnowledgeBase()
        self.min_confidence = 0.7  # hanya terapkan jika yakin 70%+
        self.rollback_states: Dict[str, str] = {}  # file_path -> original_code

    def fix(self, file_path: str, code: str, features: List[Any] = None,
            dry_run: bool = True, auto_confirm: bool = False) -> Tuple[Optional[str], int]:
        """
        Multi-pass fix dengan confidence threshold.
        Returns: (patched_code, fixes_applied)
        """
        if features is None:
            return None, 0

        # Simpan state awal untuk rollback
        self.rollback_states[file_path] = code

        patched = code
        fixes_applied = 0
        passes = 3  # maksimal 3 pass

        for _pass in range(passes):
            pass_fixes = 0
            for finding in features:
                # Cek confidence dari Knowledge Base
                confidence = self.kb.get_confidence(finding)
                if confidence < self.min_confidence:
                    continue  # tidak cukup yakin

                fix = self._generate_fix_v3(finding, patched)
                if fix:
                    new_code = self._apply_fix(patched, fix)
                    if new_code != patched and self._is_valid_pine(new_code):
                        patched = new_code
                        pass_fixes += 1
                        fixes_applied += 1

            if pass_fixes == 0:
                break  # tidak ada perbaikan di pass ini, hentikan

            # Setelah pass pertama, re-ekstrak fitur dari kode yang sudah diperbaiki
            if _pass < passes - 1:
                features = self._re_extract(patched)

        if patched == code:
            return None, 0

        # Tampilkan diff
        diff = self._generate_diff(code, patched, file_path)
        print(diff)

        if dry_run:
            print(f"\n  🔍 DRY-RUN: {fixes_applied} perbaikan siap diterapkan")
            print(f"  Gunakan --apply untuk menerapkan.")
            return patched, fixes_applied

        if not auto_confirm:
            response = input(f"\n  ⚠️  {fixes_applied} perbaikan akan diterapkan. Lanjutkan? [y/N]: ").strip().lower()
            if response != 'y':
                print(f"  ❌ Dibatalkan.")
                return None, 0

        # Backup + tulis
        backup_path = file_path + '.bak'
        shutil.copy2(file_path, backup_path)
        print(f"  📦 Backup: {backup_path}")

        try:
            with open(file_path, 'w') as f:
                f.write(patched)
            print(f"  ✅ {fixes_applied} perbaikan diterapkan ke {file_path}")
        except Exception as e:
            # Rollback
            shutil.copy2(backup_path, file_path)
            print(f"  ❌ Gagal menulis, rollback ke backup")
            return None, 0

        return patched, fixes_applied

    def rollback(self, file_path: str) -> bool:
        """Kembalikan file ke state sebelum fix."""
        if file_path in self.rollback_states:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.rollback_states[file_path])
                return True
            except Exception:
                pass
        return False

    def _generate_fix_v3(self, finding: Any, code: str) -> Optional[Dict[str, Any]]:
        """Generate perbaikan engineer-grade."""
        detector_id = getattr(finding, 'detector_id', '')

        # 1. Cek Knowledge Base untuk template fix
        template = self.kb.get_fix_template(detector_id)
        if template:
            return {
                'type': 'template',
                'template': template,
                'detector_id': detector_id,
                'description': f'KB fix: {getattr(finding, "goal", "")}'
            }

        # 2. Perbaikan struktural untuk objek dalam if/loop
        if 'obj_in_if' in detector_id or 'drawing_in_loop' in detector_id:
            return self._fix_object_in_conditional(finding, code)

        # 3. Perbaikan untuk duplicate code (pola berulang)
        if 'magic_number' in detector_id:
            return self._fix_magic_number(finding, code)

        return None

    def _fix_object_in_conditional(self, finding: Any, code: str) -> Optional[Dict[str, Any]]:
        """Perbaiki objek di dalam if/loop: pindahkan deklarasi ke luar."""
        goal = getattr(finding, 'goal', '')
        # Ekstrak nama fungsi dari goal (misal: "box.new di dalam if -> ..." → "box.new")
        import re
        match = re.search(r'(\\w+\\.new)', goal)
        if match:
            func_name = match.group(1)
            var_name = func_name.split('.')[0] + '_var'
            return {
                'type': 'restructure',
                'description': f'Pindahkan {func_name} ke deklarasi var di luar if/loop',
                'declaration': f'var {var_name} = na',
                'replacement': f'{var_name} := {func_name}(...)',
                'func_name': func_name,
                'var_name': var_name
            }
        return None

    def _fix_magic_number(self, finding: Any, code: str) -> Optional[Dict[str, Any]]:
        """Ganti magic number dengan konstanta bernama."""
        return {
            'type': 'constant',
            'description': 'Ganti magic number dengan konstanta bernama',
            'template': 'const LENGTH = {value}'
        }

    def _apply_fix(self, code: str, fix: Dict[str, Any]) -> str:
        """Terapkan perbaikan ke kode."""
        fix_type = fix.get('type', '')

        if fix_type == 'template':
            template = fix.get('template', '')
            detector_id = fix.get('detector_id', '')
            if 'request_security' in detector_id:
                import re
                pattern = r'(request\\.security\\([^)]*?)\\)'
                for m in re.finditer(pattern, code):
                    call = m.group(1)
                    if 'lookahead' not in call:
                        new_call = call.rstrip(')') + ', ' + template.split('=')[0].strip() + ' = ' + template.split('=')[1].strip() + ')'
                        return code.replace(m.group(1), new_call, 1)

        if fix_type == 'restructure':
            declaration = fix.get('declaration', '')
            func_name = fix.get('func_name', '')
            var_name = fix.get('var_name', '')
            # Tambahkan deklarasi var di awal kode (setelah indicator)
            if declaration not in code:
                code = code.replace('indicator(', 'indicator(...)\n' + declaration + '\n\n', 1)

        return code

    def _is_valid_pine(self, code: str) -> bool:
        """Cek apakah kode masih valid Pine setelah perbaikan."""
        try:
            from engine.parser import PineAST
            PineAST(code)
            return True
        except Exception:
            return False

    def _re_extract(self, code: str) -> List[Any]:
        """Re-ekstrak fitur dari kode yang sudah diperbaiki."""
        try:
            from engine.parser import PineAST
            from engine.extractor import FeatureExtractor
            ast = PineAST(code)
            extractor = FeatureExtractor(ast.root, code)
            return extractor.extract_all()
        except Exception:
            return []

    def _generate_diff(self, original: str, patched: str, file_path: str) -> str:
        return ''.join(difflib.unified_diff(
            original.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile=f'a/{file_path}',
            tofile=f'b/{file_path}',
        ))
