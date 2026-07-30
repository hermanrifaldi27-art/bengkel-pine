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
                    if self._pattern_matches(p, ast, code):
                        matched.append(rule)
                        break
                if rule in matched:
                    break
        return matched

    def _pattern_matches(self, pattern: Dict, ast, code: str) -> bool:
        node_type = pattern.get('node_type', '')
        context = pattern.get('context', '')
        contains = pattern.get('contains', '')
        not_contains = pattern.get('not_contains', '')
        signature = pattern.get('signature', '')
        
        if contains and contains not in code:
            return False
        if not_contains and not_contains in code:
            return False
        
        if node_type == 'var_declaration' and context == 'STATE':
            if 'var int' in code and '= na' in code:
                return True
            return False
        if node_type == 'function_definition' and context == 'FUNCTIONS':
            if re.search(r'(?:method\s+)?\w+\s*\([^)]*\)\s*=>\s*\{.*?return', code, re.DOTALL):
                return True
            return False
        if node_type == 'plot_call' and context == 'PLOTS':
            if re.search(r'if\s+[^:\n]*:\s*\n\s*plot\s*\(', code):
                return True
            return False
        if node_type == 'matrix_new_call':
            if re.search(r'matrix\.new', code):
                return True
            return False
        if node_type == 'for_loop':
            if re.search(r'\bfor\s+', code):
                return True
            return False
        return False
