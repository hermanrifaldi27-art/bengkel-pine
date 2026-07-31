import os

fixes_applied = 0

# ============================================================
# FIX #1: semantic.py - Add scopes attribute to __init__
# ============================================================
p = 'engine/semantic.py'
if os.path.exists(p):
    with open(p) as f:
        c = f.read()
    
    # Cek apakah scopes sudah diinisialisasi di __init__
    if 'class SemanticAnalyzer' in c and 'self.scopes' not in c[:500]:
        # Tambahkan self.scopes = {} di __init__
        old_init = """    def __init__(self, ast: PineAST):
        self.ast = ast
        self.errors = []
        self.warnings = []"""
        
        new_init = """    def __init__(self, ast: PineAST):
        self.ast = ast
        self.scopes = {}
        self.errors = []
        self.warnings = []"""
        
        if old_init in c:
            c = c.replace(old_init, new_init)
            print("✅ FIX #1: semantic.py - Added self.scopes = {} to __init__")
            fixes_applied += 1
        else:
            print("⚠️  FIX #1: semantic.py - __init__ pattern not found")
        
        with open(p, 'w') as f:
            f.write(c)
else:
    print("❌ FIX #1: semantic.py not found")

# ============================================================
# FIX #2: extractor.py - Check Feature hash/eq
# ============================================================
p = 'engine/extractor.py'
if os.path.exists(p):
    with open(p) as f:
        c = f.read()
    
    # Cek apakah Feature sudah punya hash/eq yang benar
    if 'class Feature' in c:
        if 'def __hash__' not in c or 'def __eq__' not in c:
            # Tambahkan hash/eq methods
            class_end = c.find('\nclass ', c.find('class Feature'))
            if class_end == -1:
                class_end = len(c)
            
            hash_eq = """
    def __hash__(self) -> int:
        return hash((getattr(self, 'detector_id', None), 
                    getattr(self, 'module', None),
                    getattr(self, 'goal', None),
                    getattr(self, 'tactic', None),
                    getattr(self, 'context', None)))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Feature):
            return False
        return (getattr(self, 'detector_id', None) == getattr(other, 'detector_id', None) and
                getattr(self, 'module', None) == getattr(other, 'module', None) and
                getattr(self, 'goal', None) == getattr(other, 'goal', None) and
                getattr(self, 'tactic', None) == getattr(other, 'tactic', None) and
                getattr(self, 'context', None) == getattr(other, 'context', None))
"""
            c = c[:class_end] + hash_eq + c[class_end:]
            print("✅ FIX #2: extractor.py - Added Feature.__hash__ and __eq__")
            fixes_applied += 1
        else:
            print("✅ FIX #2: extractor.py - Feature already has __hash__ and __eq__")
        
        with open(p, 'w') as f:
            f.write(c)
else:
    print("❌ FIX #2: extractor.py not found")

# ============================================================
# FIX #3: scoring.py - Check calculate() completeness
# ============================================================
p = 'engine/scoring.py'
if os.path.exists(p):
    with open(p) as f:
        c = f.read()
    
    # Cek apakah calculate() sudah ada dan complete
    if 'def calculate' in c:
        # Cek apakah ada return statement
        calc_start = c.find('def calculate')
        calc_end = c.find('\n    def ', calc_start + 1)
        if calc_end == -1:
            calc_end = len(c)
        
        calc_body = c[calc_start:calc_end]
        
        if 'return {' not in calc_body or 'total_score' not in calc_body:
            print("⚠️  FIX #3: scoring.py - calculate() exists but may be incomplete")
        else:
            print("✅ FIX #3: scoring.py - calculate() already complete")
    else:
        print("⚠️  FIX #3: scoring.py - calculate() not found")
else:
    print("❌ FIX #3: scoring.py not found")

print(f"\n🔄 Total fixes applied: {fixes_applied}")
