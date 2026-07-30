import re
from typing import Dict, Any

class PatchExecutor:
    def __init__(self, code: str, context: Dict = None):
        self.code = code
        self.context = context or {}

    def apply(self, rule: Dict, resolved: Dict[str, Any]) -> str:
        action = rule.get('action', {})
        operation = action.get('operation', '')
        anchor = action.get('anchor', '')
        template = action.get('template', '')
        target_module = action.get('target_module', '')

        # Type-aware: jika target variabel ada di matrices, ubah template matrix
        target_var = resolved.get('var')
        if target_var and target_var in self.context.get('matrices', []):
            # Pastikan template matrix, bukan array
            if 'array.shift' in template:
                template = template.replace('array.shift', 'matrix.remove_row')
                template = re.sub(r'array\.size\(([^)]+)\)', r'matrix.rows(\1)', template)

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
            return self._replace(template, anchor)
        elif operation == 'move_to_global':
            return self._move_to_global(template)
        elif operation == 'wrap_with':
            return self._wrap_with(anchor, template)
        elif operation == 'add_prefix':
            return self._add_prefix(anchor, template)
        elif operation == 'add_parameter':
            return self._add_parameter(anchor, template)
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

    def _replace(self, template: str, anchor: str) -> str:
        if not template:
            return self.code
        if '{' in template and '}' in template:
            return self.code
        if anchor:
            lines = self.code.splitlines(keepends=True)
            new_lines = []
            replaced = False
            for line in lines:
                if anchor in line and not replaced:
                    new_lines.append(template + '\n')
                    replaced = True
                else:
                    new_lines.append(line)
            if not replaced:
                new_lines.append(template + '\n')
            return ''.join(new_lines)
        return template

    def _move_to_global(self, template: str) -> str:
        return self.code + '\n' + template

    def _wrap_with(self, keyword: str, template: str) -> str:
        lines = self.code.splitlines(keepends=True)
        new_lines = []
        wrapped = False
        for line in lines:
            if keyword in line and not wrapped:
                indent = re.match(r'^(\s*)', line).group(1) if line.strip() else ''
                new_lines.append(indent + template + '\n')
                new_lines.append(indent + '    ' + line.strip() + '\n')
                new_lines.append(indent + 'end\n')
                wrapped = True
            else:
                new_lines.append(line)
        if not wrapped:
            new_lines.append(template + '\n')
        return ''.join(new_lines)

    def _add_prefix(self, prefix: str, template: str) -> str:
        lines = self.code.splitlines(keepends=True)
        new_lines = []
        for line in lines:
            if prefix in line:
                new_lines.append(line.replace(prefix, template + prefix))
            else:
                new_lines.append(line)
        return ''.join(new_lines)

    def _add_parameter(self, anchor: str, template: str) -> str:
        lines = self.code.splitlines(keepends=True)
        new_lines = []
        for line in lines:
            if anchor in line:
                match = re.search(r'\(([^)]*)\)', line)
                if match:
                    existing = match.group(1)
                    new_line = line.replace('(' + existing + ')', '(' + existing + ', ' + template + ')')
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        return ''.join(new_lines)
