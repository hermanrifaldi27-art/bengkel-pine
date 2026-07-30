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
            # Tidak ada postcondition, anggap berhasil (compiler akan cek nanti)
            return True, "Tidak ada postcondition, dianggap berhasil"

        func = post.get('function', 'array.size')
        var = resolved.get('var', '')
        operator = post.get('operator', '<=')
        value = resolved.get('limit', 100)

        # Cek literal
        literal = rf'{func}\({var}\)\s*{operator}\s*{value}'
        if re.search(literal, self.patched):
            return True, f"Postcondition terpenuhi (literal): {func}({var}) {operator} {value}"

        # Cek logis (while > limit)
        if operator == '<=':
            while_pattern = rf'while\s+{func}\({var}\)\s*>\s*{value}'
            if re.search(while_pattern, self.patched):
                return True, f"Postcondition terpenuhi (logis): while {func}({var}) > {value}"

        return False, f"Postcondition GAGAL: {func}({var}) {operator} {value} tidak terpenuhi"
