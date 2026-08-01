#!/usr/bin/env python3
"""
Pine Preprocessor — Implementasi sesuai dokumentasi resmi TradingView.
Sumber: https://www.tradingview.com/pine-script-docs/v3/appendix/pine-script-v2-preprocessor/

8 langkah:
1. Remove comments
2. Normalize newlines
3. Add trailing \n
4. Blank lines → empty strings
5. |INDENT| tokens (4 spaces / tab)
6. |B|, |E|, |EMPTY| tokens
7. Join continued lines
8. |BEGIN|, |END|, |PE| block tokens
"""

import re
from typing import List


class PinePreprocessor:
    def process(self, raw_code: str) -> str:
        code = raw_code

        # Step 1: Remove comments
        code = self._remove_comments(code)

        # Step 2: Normalize newlines
        code = self._normalize_newlines(code)

        # Step 3: Add trailing \n
        if not code.endswith('\n'):
            code += '\n'

        # Step 4: Blank lines → empty strings
        lines = code.split('\n')
        lines = [line if line.strip() else '' for line in lines]

        # Step 5: |INDENT| tokens
        lines = self._add_indent_tokens(lines)

        # Step 6: |B|, |E|, |EMPTY|
        lines = self._add_begin_end_tokens(lines)

        # Step 7: Join continued lines
        lines = self._join_continued_lines(lines)

        # Step 8: |BEGIN|, |END|, |PE|
        lines = self._add_block_tokens(lines)

        return '\n'.join(lines)

    def _remove_comments(self, code: str) -> str:
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        return code

    def _normalize_newlines(self, code: str) -> str:
        return code.replace('\r\n', '\n').replace('\r', '\n')

    def _add_indent_tokens(self, lines: List[str]) -> List[str]:
        new_lines = []
        for line in lines:
            if not line.strip():
                new_lines.append(line)
                continue
            indent_count = 0
            i = 0
            while i < len(line):
                if line[i] == ' ':
                    j = i
                    while j < len(line) and line[j] == ' ':
                        j += 1
                    indent_count += (j - i) // 4
                    i = j
                elif line[i] == '\t':
                    indent_count += 1
                    i += 1
                else:
                    break
            if indent_count > 0:
                indent_tokens = '|INDENT|' * indent_count
                rest = line.lstrip(' \t')
                new_lines.append(indent_tokens + rest)
            else:
                new_lines.append(line)
        return new_lines

    def _add_begin_end_tokens(self, lines: List[str]) -> List[str]:
        result = []
        for line in lines:
            if not line.strip():
                result.append('|EMPTY|')
            else:
                result.append(f'|B|{line}|E|')
        return result

    def _join_continued_lines(self, lines: List[str]) -> List[str]:
        CONT = {',', '?', ':', '+', '-', '*', '/', '%',
                '=', '<', '>', '&', '^', '~'}
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip() == '|EMPTY|':
                i += 1
                continue
            content = line
            if content.startswith('|B|'):
                content = content[3:]
            if content.endswith('|E|'):
                content = content[:-3]
            cs = content.rstrip()
            if cs.endswith('=>'):
                i += 1
                continue
            if cs and cs[-1] in CONT:
                j = i + 1
                while j < len(lines) and lines[j].strip() == '|EMPTY|':
                    j += 1
                if j < len(lines):
                    nl = lines[j]
                    if nl.startswith('|B|'):
                        nl = nl[3:]
                    if nl.endswith('|E|'):
                        nl = nl[:-3]
                    while nl.startswith('|INDENT|'):
                        nl = nl[8:]
                    combined = f'{cs} {nl.lstrip()}'
                    lines[i] = f'|B|{combined}|E|'
                    del lines[j]
                    continue
            i += 1
        return lines

    def _add_block_tokens(self, lines: List[str]) -> List[str]:
        # Ekstrak indent level dan konten TANPA |INDENT|
        processed = []
        for line in lines:
            if line.strip() == '|EMPTY|':
                processed.append((0, None))
                continue
            content = line
            if content.startswith('|B|'):
                content = content[3:]
            if content.endswith('|E|'):
                content = content[:-3]
            indent_count = 0
            temp = content
            while temp.startswith('|INDENT|'):
                indent_count += 1
                temp = temp[8:]
            processed.append((indent_count, temp))

        final_lines = []
        prev_indent = 0
        i = 0
        while i < len(processed):
            indent, content = processed[i]

            if content is None:
                final_lines.append('|EMPTY|')
                i += 1
                continue

            # Baris tanpa |INDENT|
            line_str = f'|B|{content}|E|'

            if indent > prev_indent:
                final_lines.append(f'|BEGIN|{line_str}')
                prev_indent = indent
                i += 1
                continue

            if indent < prev_indent:
                diff = prev_indent - indent
                end_tokens = '|END||PE|' * diff
                if final_lines:
                    final_lines[-1] += end_tokens
                else:
                    final_lines.append(end_tokens)
                prev_indent = indent
                final_lines.append(line_str)
                i += 1
                continue

            final_lines.append(line_str)
            i += 1

        # Tutup blok tersisa
        while prev_indent > 0:
            end_tokens = '|END||PE|'
            if final_lines:
                final_lines[-1] += end_tokens
            else:
                final_lines.append(end_tokens)
            prev_indent -= 1

        return final_lines
