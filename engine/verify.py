import re
from typing import Dict, Any, Tuple

class VerificationEngine:
    def __init__(self, original_code: str, patched_code: str):
        self.original = original_code
        self.patched = patched_code

    def verify(self, rule: Dict, resolved: Dict[str, Any]) -> Tuple[bool, str]:
        verification = rule.get('verification', {})
        post = verification.get('post_condition', {})
        if not post:
            if self.patched == self.original:
                return False, "Kode tidak berubah setelah patch"
            return True, "Tidak ada postcondition, dianggap berhasil"
        
        func = post.get('function', 'array.size')
        var = resolved.get('var', '')
        operator = post.get('operator', '<=')
        value = resolved.get('limit', post.get('value', 100))
        
        literal = rf'{re.escape(func)}\({re.escape(var)}\)\s*{re.escape(operator)}\s*{value}'
        if re.search(literal, self.patched):
            return True, f"Postcondition terpenuhi (literal): {func}({var}) {operator} {value}"
        
        if operator == '<=' and 'array' in func:
            while_pattern = rf'while\s+{re.escape(func)}\({re.escape(var)}\)\s*>\s*{value}'
            if re.search(while_pattern, self.patched):
                return True, f"Postcondition terpenuhi (logis): while {func}({var}) > {value}"
        
        if 'matrix' in func or 'rows' in func:
            if_pattern = rf'if\s+{re.escape(func)}\({re.escape(var)}\)\s*>\s*{value}'
            while_pattern = rf'while\s+{re.escape(func)}\({re.escape(var)}\)\s*>\s*{value}'
            if re.search(if_pattern, self.patched) or re.search(while_pattern, self.patched):
                return True, f"Postcondition terpenuhi (matrix): {func}({var}) > {value} di-handle"
        
        if var and f'{var}' in self.patched:
            if any(kw in self.patched for kw in ['remove_row', 'array.shift', 'array.slice', '.shift(', '.remove_row(']):
                return True, f"Postcondition longgar terpenuhi: ada operasi eviction pada {var}"
        
        return False, f"Postcondition GAGAL: {func}({var}) {operator} {value} tidak terpenuhi"
