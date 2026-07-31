p = '/sdcard/bengkel-pine/engine/parser.py'
with open(p) as f:
    c = f.read()

changes = 0

# ============================================================
# FIX BUG #3: Regex hanya capture 1 group, harusnya 2
# ============================================================
# Cari pattern yang broken
old_broken = """    def _extract_symbols_fallback(self):
        import re
        for m in re.finditer(r'(?:var|varip)\s+(?:(?:array|matrix)(?:<[^>]+>)?\s+)?(\w+)\s*=\s*(?:array|matrix)\.new', self.code):
            name, kind = m.group(1), m.group(2)"""

new_fixed = """    def _extract_symbols_fallback(self):
        import re
        for m in re.finditer(r'(?:var|varip)\s+(?:(array|matrix)(?:<[^>]+>)?\s+)?(\w+)\s*=\s*(array|matrix)\.new', self.code):
            kind_hint, name, kind = m.group(1), m.group(2), m.group(3)
            if not kind:
                kind = kind_hint  # fallback ke type annotation jika ada"""

if old_broken in c:
    c = c.replace(old_broken, new_fixed)
    print("✅ BUG #3: regex fixed to capture 2 groups (name + kind)")
    changes += 1
else:
    print("❌ BUG #3: pattern not found")
    # Show context
    fallback_idx = c.find('def _extract_symbols_fallback')
    if fallback_idx >= 0:
        print(f"Context: {c[fallback_idx:fallback_idx+300]}")

# ============================================================
# FIX BUG #2: Empty block tanpa indentasi infinite loop
# ============================================================
# Cari bagian else di _parse_block
# Baca actual code structure
import re

# Cari semua 'else:' dalam _parse_block
block_start = c.find('def _parse_block(self):')
if block_start >= 0:
    # Cari next function definition
    block_end = c.find('\n    def ', block_start + 1)
    if block_end < 0:
        block_end = len(c)
    
    block_code = c[block_start:block_end]
    
    # Cari pattern else: while ... tanpa pos check
    # Pattern: else:\n            while ... NEWLINE:\n                ...parse_statement...
    # tapi TIDAK ada "if self.pos == old_pos"
    
    if 'else:' in block_code and 'if self.pos == old_pos' not in block_code:
        # Tambahkan guard di semua while loop dalam else branch
        # Cari: else:\n            while self._peek() and self._peek().type != TokenType.NEWLINE:
        else_pattern = r'(        else:\n            while self\._peek$$ and self\._peek$$\.type != TokenType\.NEWLINE:\n                self\._skip_comments_and_newlines$$\n)(                stmt = self\.parse_statement$$)'
        
        match = re.search(else_pattern, block_code)
        if match:
            replacement = match.group(1) + '                old_pos = self.pos\n' + match.group(2) + '\n                if stmt: stmts.append(stmt)\n                if self.pos == old_pos: self._next()'
            new_block = block_code.replace(match.group(0), replacement)
            c = c[:block_start] + new_block + c[block_end:]
            print("✅ BUG #2: infinite loop guard added to else branch")
            changes += 1
        else:
            print("⚠️  BUG #2: else pattern not found in _parse_block")
            # Manual inspection
            lines = block_code.split('\n')
            for i, line in enumerate(lines):
                if 'else:' in line and i < len(lines) - 5:
                    print(f"   Found else at line {i}: {line}")
                    print(f"   Next lines: {lines[i+1:i+6]}")
    else:
        print("⚠️  BUG #2: else branch already has pos check or not found")

with open(p, 'w') as f:
    f.write(c)

print(f"\n🔄 Total changes: {changes}/2")
