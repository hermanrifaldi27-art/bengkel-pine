import re

class RuleMatcher:
    def __init__(self, rules):
        self.rules = rules
    
    def match_by_error(self, error_text):
        matched = []
        for rule in self.rules:
            triggers = rule.get('triggers', [])
            for t in triggers:
                if t.get('type') == 'compiler':
                    signals = t.get('error_signals', [])
                    for pattern in signals:
                        # Bersihkan error_text dari "line X: " jika ada
                        clean_error = re.sub(r'^line\s+\d+:\s*', '', error_text)
                        # Bersihkan pattern dari "line \\d+: " jika ada
                        clean_pattern = re.sub(r'^line\\s+\\d+:\s*', '', pattern)
                        if re.search(clean_pattern, clean_error) or re.search(pattern, error_text):
                            matched.append(rule)
                            break
                elif t.get('type') == 'analyzer':
                    # Untuk analyzer, kita tidak perlu match error, tapi kita bisa abaikan dulu
                    # Atau kita bisa cek AST patterns (belum diimplementasikan)
                    pass
            if rule in matched:
                break
        return matched
