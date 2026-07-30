import re
from typing import Dict, Any

class PatchExecutor:
    def __init__(self, code: str):
        self.code = code

    def apply(self, rule: Dict, resolved: Dict[str, Any]) -> str:
        action = rule.get('action', {})
        operation = action.get('operation', '')
        anchor = action.get('anchor', '')
        template = action.get('template', '')
        
        for key, val in resolved.items():
            if val is None:
                continue
            template = template.replace(f'{{{key}}}', str(val))
            anchor = anchor.replace(f'{{{key}}}', str(val))
        
        if operation == 'remove_keyword':
            return self._remove_keyword(anchor)
        elif operation == 'inject_after':
            return self._inject_after(anchor, template)
        elif operation == 'replace_pattern':
            return self._replace_pattern(anchor, template)
        elif operation == 'replace':
            if '{' in template and '}' in template:
                return self.code
            return self._replace(template)
        else:
            return self.code

    def _remove_keyword(self, keyword: str) -> str:
        lines = self.code.splitlines(keepends=True)
        new_lines = []
        for line in lines:
            if re.search(rf'\b{re.escape(keyword)}\b', line):
                continue
            new_lines.append(line)
        return ''.join(new_lines)

    def _inject_after(self, anchor: str, template: str) -> str:
        if not anchor or not template:
            return self.code
        lines = self.code.splitlines(keepends=True)
        new_lines = []
        injected = False
        for line in lines:
            new_lines.append(line)
            if not injected and anchor in line:
                indent = re.match(r'^(\s*)', line).group(1) if line.strip() else ''
                for t in template.splitlines():
                    new_lines.append(indent + t + '\n')
                injected = True
        return ''.join(new_lines)

    def _replace_pattern(self, pattern: str, replacement: str) -> str:
        try:
            return re.sub(pattern, replacement, self.code)
        except re.error:
            return self.code

    def _replace(self, template: str) -> str:
        return template
