import re
from typing import List, Dict, Any

class RuleMatcher:
    def __init__(self, rules: List[Dict]):
        self.rules = rules

    def match_by_error(self, error_text: str) -> List[Dict]:
        matched = []
        for rule in self.rules:
            triggers = rule.get('triggers', [])
            for t in triggers:
                if t.get('type') == 'compiler':
                    signals = t.get('error_signals', [])
                    for pattern in signals:
                        clean_error = re.sub(r'^line\s+\d+:\s*', '', error_text, flags=re.IGNORECASE)
                        clean_pattern = re.sub(r'^line\\s\+\\d\+:\s*', '', pattern)
                        clean_pattern = re.sub(r'^line\s+\d+:\s*', '', clean_pattern)
                        try:
                            if re.search(clean_pattern, clean_error, re.IGNORECASE) or \
                               re.search(pattern, error_text, re.IGNORECASE):
                                matched.append(rule)
                                break
                        except re.error:
                            continue
                if rule in matched:
                    break
        return matched

    def match_by_ast(self, ast) -> List[Dict]:
        code = ast.code
        matched = []
        for rule in self.rules:
            triggers = rule.get('triggers', [])
            for t in triggers:
                if t.get('type') != 'analyzer':
                    continue
                patterns = t.get('ast_patterns', [])
                for p in patterns:
                    if self._pattern_matches(p, code):
                        matched.append(rule)
                        break
                if rule in matched:
                    break
        return matched

    def _pattern_matches(self, pattern: Dict, code: str) -> bool:
        node_type = pattern.get('node_type', '')
        context = pattern.get('context', '')
        contains = pattern.get('contains', '')
        not_contains = pattern.get('not_contains', '')
        # Cek contains / not_contains
        if contains and contains not in code:
            return False
        if not_contains and not_contains in code:
            return False
        # Node type spesifik
        if node_type == 'comparison' and 'array.size' in code and 'array.push' in code:
            return True
        if node_type == 'var_declaration' and context == 'STATE' and 'var int' in code and '= na' in code:
            return True
        if node_type == 'function_definition' and context == 'FUNCTIONS' and 'return' in code:
            return True
        if node_type == 'plot_call' and context == 'PLOTS' and re.search(r'if\s+[^:\n]*:\s*\n\s*plot\s*\(', code):
            return True
        if node_type == 'matrix_new_call' and 'matrix.new' in code and 'matrix.add_row' in code:
            return True
        return False
