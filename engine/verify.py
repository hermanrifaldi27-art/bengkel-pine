import re
from typing import Dict, Any, Tuple

class VerificationEngine:
    def __init__(self, original_code: str, patched_code: str, context: Dict = None):
        self.original = original_code
        self.patched = patched_code
        self.context = context or {}

    def verify(self, rule: Dict, resolved: Dict[str, Any]) -> Tuple[bool, str]:
        # 1. Kode berubah?
        if self.patched == self.original:
            return False, "Kode tidak berubah setelah patch"

        # 2. Tidak ada placeholder tersisa?
        remaining = re.findall(r'\{[a-z_]+\}', self.patched)
        if remaining:
            return False, f"Placeholder tidak terisi: {remaining}"

        # 3. Variabel target ada di kode?
        target_var = resolved.get('var')
        if target_var and target_var not in self.patched:
            return False, f"Variabel target '{target_var}' tidak ditemukan di kode hasil patch"

        # 4. Type consistency: matrix tidak boleh pakai array.*
        matrices = self.context.get('matrices', [])
        for mvar in matrices:
            if f"array.size({mvar})" in self.patched:
                return False, f"array.size() digunakan pada matrix '{mvar}'"
            if f"array.shift({mvar})" in self.patched:
                return False, f"array.shift() digunakan pada matrix '{mvar}'"
            if f"array.push({mvar})" in self.patched:
                return False, f"array.push() digunakan pada matrix '{mvar}'"

        # 5. Postcondition (jika ada)
        verification = rule.get('verification', {})
        post = verification.get('post_condition', {})
        if post:
            func = post.get('function', 'array.size')
            var = resolved.get('var', '')
            operator = post.get('operator', '<=')
            value = resolved.get('limit', post.get('value', 100))

            # 5a. Cek literal: array.size(var) <= value
            literal = rf'{re.escape(func)}\({re.escape(var)}\)\s*{re.escape(operator)}\s*{value}'
            if re.search(literal, self.patched):
                return True, f"Postcondition terpenuhi (literal): {func}({var}) {operator} {value}"

            # 5b. Logis: while array.size(var) > value → menjamin <= value
            if operator == '<=':
                while_pattern = rf'while\s+{re.escape(func)}\({re.escape(var)}\)\s*>\s*{value}'
                if re.search(while_pattern, self.patched):
                    return True, f"Postcondition terpenuhi (logis): while {func}({var}) > {value}"

            # 5c. Logis matrix: if matrix.rows(var) > value
            if 'matrix' in func or 'rows' in func:
                if_pattern = rf'if\s+{re.escape(func)}\({re.escape(var)}\)\s*>\s*{value}'
                while_pattern = rf'while\s+{re.escape(func)}\({re.escape(var)}\)\s*>\s*{value}'
                if re.search(if_pattern, self.patched) or re.search(while_pattern, self.patched):
                    return True, f"Postcondition terpenuhi (matrix): {func}({var}) > {value} di-handle"

            return False, f"Postcondition GAGAL: {func}({var}) {operator} {value} tidak terpenuhi"

        return True, "Verifikasi OK"
