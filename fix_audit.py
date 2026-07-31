import re

p = '/sdcard/bengkel-pine/engine/parser.py'
with open(p) as f:
    c = f.read()

changes = 0

# ============================================================
# BUG #1 (KRITIS): Arrow function tidak support generic type
# ============================================================
# Cari fungsi lama dan replace sepenuhnya
old_arrow = None
new_arrow = '''    def _parse_arrow_params_after_open(self):
        params = []
        while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == ')'):
            self._skip_comments_and_newlines()
            if not self._peek(): break
            typ = None
            # Gunakan _parse_type untuk menangani generic/qualified type
            typ = self._parse_type()
            name_tok = self._expect(TokenType.IDENTIFIER)
            default = None
            if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '=':
                self._next(); default = self.parse_expr(0)
            if name_tok:
                params.append({'name': name_tok.value, 'type': typ, 'default': default})
            if self._peek() and self._peek().type == TokenType.COMMA:
                self._next()
        if not (self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == ')'):
            return None
        self._next()
        return params'''

# Cari start dan end dari fungsi lama
lines = c.split('\n')
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if '    def _parse_arrow_params_after_open(self):' in line:
        start_idx = i
    elif start_idx is not None and end_idx is None:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped.startswith('def ') and indent <= 4:
            end_idx = i
            break

if start_idx is not None:
    if end_idx is None:
        end_idx = len(lines)
    old_func = '\n'.join(lines[start_idx:end_idx])
    c = c.replace(old_func, new_arrow + '\n')
    print(f"✅ BUG #1: _parse_arrow_params_after_open replaced (lines {start_idx+1}-{end_idx})")
    changes += 1
else:
    print("❌ BUG #1: _parse_arrow_params_after_open not found!")

# ============================================================
# BUG #2 (SEDANG): Empty block tanpa indentasi infinite loop
# ============================================================
# Cari bagian else di _parse_block yang tidak punya infinite loop guard
# Pattern: while loop tanpa pos check di else branch
old_block_else = """        else:
            while self._peek() and self._peek().type != TokenType.NEWLINE:
                self._skip_comments_and_newlines()
                stmt = self.parse_statement()
                if stmt: stmts.append(stmt)"""

new_block_else = """        else:
            while self._peek() and self._peek().type != TokenType.NEWLINE:
                self._skip_comments_and_newlines()
                old_pos = self.pos
                stmt = self.parse_statement()
                if stmt: stmts.append(stmt)
                if self.pos == old_pos: self._next()"""

if old_block_else in c:
    c = c.replace(old_block_else, new_block_else)
    print("✅ BUG #2: _parse_block else branch: infinite loop guard added")
    changes += 1
else:
    # Coba pattern alternatif
    # Cari semua while di _parse_block
    print("⚠️  BUG #2: pattern exact not found, trying alternate...")
    
    # Cari dengan regex
    pattern = r'(        else:\n            while self\._peek$$ and self\._peek$$\.type != TokenType\.NEWLINE:\n                self\._skip_comments_and_newlines$$\n)(                stmt = self\.parse_statement$$\n                if stmt: stmts\.append$stmt$)'
    match = re.search(pattern, c)
    if match:
        replacement = match.group(1) + '                old_pos = self.pos\n' + match.group(2) + '\n                if self.pos == old_pos: self._next()'
        c = c.replace(match.group(0), replacement)
        print("✅ BUG #2: _parse_block else branch: infinite loop guard added (alt pattern)")
        changes += 1
    else:
        print("❌ BUG #2: Could not find _parse_block else pattern")
        # Show context for debugging
        block_start = c.find('def _parse_block')
        if block_start >= 0:
            print(f"   _parse_block found at position {block_start}")
            print(f"   Context: {c[block_start:block_start+500]}")

# ============================================================
# BUG #3 (RINGAN): Fallback regex tidak akurat
# ============================================================
# Cari regex lama di _extract_symbols_fallback
old_regex1 = r"r'var\s+(\w+)\s*=\s*(array|matrix)\.new'"
new_regex1 = r"r'(?:var|varip)\s+(?:array|matrix)(?:<[^>]+>)?\s+(\w+)\s*=\s*(?:array|matrix)\.new|var\s+(\w+)\s*=\s*(?:array|matrix)\.new'"

# Coba beberapa pattern yang mungkin
found_bug3 = False

# Pattern 1: regex langsung di kode
for old_pat in [
    r"r'var\s+(\w+)\s*=\s*(array|matrix)\.new'",
    'r"var\\s+(\\w+)\\s*=\\s*(array|matrix)\\.new"',
]:
    if old_pat in c:
        # Replace dengan versi yang lebih lengkap
        new_pat = r"r'(?:var|varip)\s+(?:(?:array|matrix)(?:<[^>]+>)?\s+)?(\w+)\s*=\s*(?:array|matrix)\.new'"
        c = c.replace(old_pat, new_pat)
        print(f"✅ BUG #3: _extract_symbols_fallback regex improved")
        changes += 1
        found_bug3 = True
        break

if not found_bug3:
    # Coba cari dengan context yang lebih luas
    fallback_start = c.find('_extract_symbols_fallback')
    if fallback_start >= 0:
        fallback_chunk = c[fallback_start:fallback_start+1000]
        print(f"⚠️  BUG #3: exact regex pattern not found. Context:")
        # Find the regex in the chunk
        regex_matches = re.findall(r"r['\"].*?['\"]", fallback_chunk)
        for m in regex_matches:
            print(f"   Found regex: {m}")
        # Try to find and replace the var regex
        for m in regex_matches:
            if 'var' in m and 'array' in m:
                new_regex = r"r'(?:var|varip)\s+(?:(?:array|matrix)(?:<[^>]+>)?\s+)?(\w+)\s*=\s*(?:array|matrix)\.new'"
                c = c.replace(m, new_regex)
                print(f"✅ BUG #3: replaced {m}")
                changes += 1
                found_bug3 = True
                break
    if not found_bug3:
        print("❌ BUG #3: Could not locate fallback regex")

with open(p, 'w') as f:
    f.write(c)

print(f"\n🔄 Total changes: {changes}/3")
