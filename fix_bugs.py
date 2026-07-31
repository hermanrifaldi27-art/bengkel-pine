import os, re

BASE = os.path.dirname(os.path.abspath(__file__))

# === Fix 1: parser.py ===
p = os.path.join(BASE, 'engine', 'parser.py')
with open(p) as f:
    lines = f.readlines()

new_lines = []
fallback_done = False
for line in lines:
    # Sisipkan fallback call setelah _extract_symbols(self.root)
    if 'self._extract_symbols(self.root)' in line and 'def ' not in line:
        new_lines.append(line)
        indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(f'{indent}self._extract_symbols_fallback()\n')
        continue

    # Sisipkan method fallback sebelum get_symbols
    if 'def get_symbols(self)' in line and not fallback_done:
        indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(f'''{indent}def _extract_symbols_fallback(self):
{indent}    import re
{indent}    for m in re.finditer(r'var\\s+(\\w+)\\s*=\\s*(array|matrix)\\.new', self.code):
{indent}        name, kind = m.group(1), m.group(2)
{indent}        if kind == 'array' and name not in self.arrays:
{indent}            self.arrays.append(name)
{indent}            self.symbols[name] = 'array'
{indent}        elif kind == 'matrix' and name not in self.matrices:
{indent}            self.matrices.append(name)
{indent}            self.symbols[name] = 'matrix'
''')
        fallback_done = True

    new_lines.append(line)

with open(p, 'w') as f:
    f.writelines(new_lines)
print("✅ parser.py: _extract_symbols_fallback added")

# === Fix 2 & 3: extractor.py ===
p = os.path.join(BASE, 'engine', 'extractor.py')
with open(p) as f:
    c = f.read()

# Fix 2: visit_VarDeclaration — cek node.type langsung
old2 = """        if node.value and isinstance(node.value, Identifier) and node.value.name == 'na':
            sym = self.semantic.get_symbol(node.name)
            if sym and sym.type and sym.type == TYPE_INT:
                self._add_feature('state', f"var int {node.name} = na -> ubah ke 0",
                    f"var int {node.name} = 0", 'STATE', 'var_int_na_v1',
                    anchor=node.span, diag_code='PINE0001')"""

new2 = """        if node.value and isinstance(node.value, Identifier) and node.value.name == 'na':
            is_int = False
            if node.type:
                tn = node.type.name if isinstance(node.type, Identifier) else getattr(node.type, 'name', None)
                if tn == 'int':
                    is_int = True
            if not is_int:
                sym = self.semantic.get_symbol(node.name)
                if sym and sym.type and sym.type == TYPE_INT:
                    is_int = True
            if is_int:
                self._add_feature('state', f"var int {node.name} = na -> ubah ke 0",
                    f"var int {node.name} = 0", 'STATE', 'var_int_na_v1',
                    anchor=node.span, diag_code='PINE0001')"""

if old2 in c:
    c = c.replace(old2, new2)
    print("✅ extractor.py: visit_VarDeclaration fixed")
else:
    print("⚠️  visit_VarDeclaration: pattern mismatch, trying line-by-line...")
    ls = c.split('\n')
    out = []
    skip = 0
    for i, line in enumerate(ls):
        if skip > 0:
            skip -= 1
            continue
        if "node.value.name == 'na'" in line and 'visit_' not in line and 'def ' not in line:
            ind = line[:len(line) - len(line.lstrip())]
            out.append(f"{ind}if node.value and isinstance(node.value, Identifier) and node.value.name == 'na':")
            out.append(f"{ind}    is_int = False")
            out.append(f"{ind}    if node.type:")
            out.append(f"{ind}        tn = node.type.name if isinstance(node.type, Identifier) else getattr(node.type, 'name', None)")
            out.append(f"{ind}        if tn == 'int':")
            out.append(f"{ind}            is_int = True")
            out.append(f"{ind}    if not is_int:")
            out.append(f"{ind}        sym = self.semantic.get_symbol(node.name)")
            out.append(f"{ind}        if sym and sym.type and sym.type == TYPE_INT:")
            out.append(f"{ind}            is_int = True")
            out.append(f"{ind}    if is_int:")
            j = i + 1
            while j < len(ls) and 'PINE0001' not in ls[j]:
                j += 1
            out.append(f"""{ind}        self._add_feature('state', f"var int {{node.name}} = na -> ubah ke 0",""")
            out.append(f"""{ind}            f"var int {{node.name}} = 0", 'STATE', 'var_int_na_v1',""")
            out.append(f"""{ind}            anchor=node.span, diag_code='PINE0001')""")
            skip = j - i
            print("✅ extractor.py: visit_VarDeclaration fixed (line-by-line)")
        else:
            out.append(line)
    c = '\n'.join(out)

# Fix 3: _check_request_security — fallback cek QualifiedName
old3 = "if actual_val and 'lookahead_off' in actual_val:"
new3 = """# Fallback: cek langsung dari AST node
                if not actual_val:
                    if isinstance(arg.value, QualifiedName):
                        actual_val = '.'.join(arg.value.parts)
                    elif isinstance(arg.value, MemberAccess):
                        actual_val = self._get_func_name(arg.value)
                    elif isinstance(arg.value, Identifier):
                        actual_val = arg.value.name
                if actual_val and 'lookahead_off' in actual_val:"""

if old3 in c:
    c = c.replace(old3, new3, 1)
    print("✅ extractor.py: _check_request_security fixed")
else:
    print("⚠️  _check_request_security: pattern not found")

with open(p, 'w') as f:
    f.write(c)

print("\n🔄 Semua patch selesai!")
