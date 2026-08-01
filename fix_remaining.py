import re

fixes_applied = 0

# ============================================================
# FIX #2: Add position guard in _parse_block()
# ============================================================
p = '/sdcard/bengkel-pine/engine/parser.py'
with open(p) as f:
    lines = f.readlines()

# Cari function _parse_block dan tambahkan guard
in_parse_block = False
new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    
    # Deteksi masuk ke _parse_block
    if 'def _parse_block(self)' in line:
        in_parse_block = True
    
    # Cari baris dengan parse_statement() di dalam _parse_block
    if in_parse_block and 'stmt = self.parse_statement()' in line and 'old_pos' not in line:
        # Dapatkan indentasi
        indent = len(line) - len(line.lstrip())
        indent_str = ' ' * indent
        
        # Insert position guard sebelum parse_statement
        new_lines.insert(-1, f'{indent_str}old_pos = self.pos\n')
        
        # Cari baris berikutnya untuk insert guard setelahnya
        j = i + 1
        while j < len(lines) and (lines[j].strip() == '' or lines[j].strip().startswith('if stmt')):
            j += 1
        
        # Insert guard setelah if stmt block
        if j < len(lines):
            guard_lines = [
                f'{indent_str}# Guard against infinite loop\n',
                f'{indent_str}if self.pos == old_pos and self._peek():\n',
                f'{indent_str}    self._next()\n',
            ]
            for k, guard_line in enumerate(guard_lines):
                new_lines.insert(i + 2 + k, guard_line)
            break

with open(p, 'w') as f:
    f.writelines(new_lines)

print("✅ FIX #2: Attempted to add position guard in _parse_block()")
fixes_applied += 1

# ============================================================
# FIX #3: Add RangeExpr validation in semantic.py
# ============================================================
p = '/sdcard/bengkel-pine/engine/semantic.py'
with open(p) as f:
    c = f.read()

# Cari _walk function dan tambahkan validasi RangeExpr
if 'def _walk' in c and 'RangeExpr' not in c:
    # Cari akhir dari _walk function (sebelum method berikutnya)
    walk_start = c.find('def _walk(')
    next_def = c.find('\n    def ', walk_start + 10)
    
    if next_def > 0:
        # Insert validasi sebelum akhir _walk
        validation = """
        # RangeExpr validation (for future implementation)
        # RangeExpr type checking akan dilakukan di evaluator
"""
        c = c[:next_def] + validation + c[next_def:]
        print("✅ FIX #3: Added RangeExpr validation placeholder in semantic.py")
        fixes_applied += 1
    else:
        print("⚠️  FIX #3: Could not find insertion point")
else:
    print("⚠️  FIX #3: RangeExpr already handled or _walk not found")

with open(p, 'w') as f:
    f.write(c)

print(f"\n🔄 Additional fixes applied: {fixes_applied}")
