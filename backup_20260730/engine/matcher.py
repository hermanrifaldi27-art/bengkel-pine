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
                        clean_error = re.sub(r'^line\s+\d+:\s*', '', error_text)
                        clean_pattern = re.sub(r'^line\\s+\\d+:\s*', '', pattern)
                        if re.search(clean_pattern, clean_error) or re.search(pattern, error_text):
                            matched.append(rule)
                            break
                if rule in matched:
                    break
        return matched

    def match_by_ast(self, ast) -> List[Dict]:
        code = ast.code
        matched = []

        for rule in self.rules:
            triggers = rule.get('triggers', [])
            for t in triggers:
                if t.get('type') == 'analyzer':
                    patterns = t.get('ast_patterns', [])
                    for p in patterns:
                        node_type = p.get('node_type', '')
                        context = p.get('context', '')
                        contains = p.get('contains', '')
                        not_contains = p.get('not_contains', '')

                        # Deteksi var int ... = na di STATE
                        if node_type == 'var_declaration' and context == 'STATE':
                            if 'var int' in code and '= na' in code:
                                matched.append(rule)
                                break

                        # Deteksi return di fungsi (jika ada)
                        elif node_type == 'function_definition' and context == 'FUNCTIONS':
                            if re.search(r'function\s+.*?=>\s*\{.*?return', code, re.DOTALL):
                                matched.append(rule)
                                break

                        # Deteksi plot di dalam if
                        elif node_type == 'plot_call' and context == 'PLOTS':
                            if re.search(r'if\s+[^:]*:\s*\n\s*plot\s*\(', code):
                                matched.append(rule)
                                break

                    if rule in matched:
                        break
        return matched
