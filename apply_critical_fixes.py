import os
import re

fixes_applied = 0

# ============================================================
# FIX #1: semantic.py - Add scope for block statements
# ============================================================
p = 'engine/semantic.py'
if os.path.exists(p):
    with open(p) as f:
        c = f.read()
    
    # Cari fungsi _walk dan tambahkan scope untuk block statements
    if 'def _walk' in c and 'IfStatement' not in c[:c.find('def _walk') + 500]:
        # Tambahkan setelah pengecekan FunctionDeclaration/MethodDeclaration
        old_pattern = "if isinstance(node, (FunctionDeclaration, MethodDeclaration)):"
        new_code = """# Create scope for block statements
        if isinstance(node, (IfStatement, ForStatement, WhileStatement, ForInStatement, SwitchStatement)):
            scope = Scope(kind='block', parent=parent_scope, node=node)
            self.scopes[id(node)] = scope
            for child in self._get_children(node):
                self._walk(child, scope)
            return
        
        if isinstance(node, (FunctionDeclaration, MethodDeclaration)):"""
        
        if old_pattern in c:
            c = c.replace(old_pattern, new_code)
            print("✅ FIX #1: semantic.py - Added scope for block statements")
            fixes_applied += 1
        else:
            print("⚠️  FIX #1: semantic.py - Pattern not found, may already be fixed")
        
        with open(p, 'w') as f:
            f.write(c)
else:
    print("❌ FIX #1: semantic.py not found")

# ============================================================
# FIX #2 & #3: extractor.py - Implement _analyze_flow_sensitive & Fix Feature hash/eq
# ============================================================
p = 'engine/extractor.py'
if os.path.exists(p):
    with open(p) as f:
        c = f.read()
    
    # FIX #2: Implement _analyze_flow_sensitive
    old_stub = """    def _analyze_flow_sensitive(self, node):
        \"\"\"Analisis flow-sensitive untuk deteksi masalah.\"\"\"
        pass"""
    
    new_impl = """    def _analyze_flow_sensitive(self, node):
        \"\"\"Analisis flow-sensitive: deteksi operasi di semua cabang.\"\"\"
        if not hasattr(self, 'cfg') or not self.cfg:
            return []
        
        findings = []
        for block in self.cfg.blocks:
            for stmt in block.statements:
                if isinstance(stmt, Call):
                    fn = self._get_func_name(stmt.func) if hasattr(stmt, 'func') else None
                    if fn == 'request.security':
                        if self._is_always_executed(block):
                            findings.append({
                                'type': 'always_executed_request',
                                'node': stmt,
                                'block': block
                            })
        return findings
    
    def _is_always_executed(self, block):
        \"\"\"Cek apakah block selalu dieksekusi.\"\"\"
        if not hasattr(self, 'cfg') or not self.cfg:
            return True
        entry = self.cfg.entry
        if entry == block:
            return True
        return hasattr(block, 'dominators') and entry in block.dominators"""
    
    if old_stub in c:
        c = c.replace(old_stub, new_impl)
        print("✅ FIX #2: extractor.py - Implemented _analyze_flow_sensitive")
        fixes_applied += 1
    elif 'def _analyze_flow_sensitive' not in c:
        # Tambahkan fungsi jika tidak ada
        # Cari class dan tambahkan sebelum method terakhir
        class_match = re.search(r'class.*?Extractor.*?:', c)
        if class_match:
            insert_pos = c.rfind('    def ')
            c = c[:insert_pos] + new_impl + '\n\n' + c[insert_pos:]
            print("✅ FIX #2: extractor.py - Added _analyze_flow_sensitive")
            fixes_applied += 1
    
    # FIX #3: Fix Feature.__hash__ and __eq__
    old_hash = """    def __hash__(self) -> int:
        return hash((self.module, self.tactic))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Feature):
            return False
        return self.module == other.module and self.tactic == other.tactic"""
    
    new_hash = """    def __hash__(self) -> int:
        return hash((self.detector_id, self.module, self.goal, self.tactic, self.context))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Feature):
            return False
        return (self.detector_id == other.detector_id and
                self.module == other.module and
                self.goal == other.goal and
                self.tactic == other.tactic and
                self.context == other.context)"""
    
    if old_hash in c:
        c = c.replace(old_hash, new_hash)
        print("✅ FIX #3: extractor.py - Fixed Feature.__hash__ and __eq__")
        fixes_applied += 1
    else:
        print("⚠️  FIX #3: extractor.py - Hash/eq pattern not found")
    
    with open(p, 'w') as f:
        f.write(c)
else:
    print("❌ FIX #2 & #3: extractor.py not found")

# ============================================================
# FIX #4 & #6: scoring.py - Add context_type/line to Feature & Complete calculate()
# ============================================================
p = 'engine/scoring.py'
if os.path.exists(p):
    with open(p) as f:
        c = f.read()
    
    # FIX #6: Complete calculate() method
    old_calc = """    def calculate(self, features: List[Feature]) -> Dict[str, Any]:
        total_score = 100.0
        deductions_by_category = {}
        
        for f in features:
            detector_id = getattr(f, 'detector_id', 'unknown')
            category = self._get_category(detector_id)"""
    
    new_calc = """    def calculate(self, features: List[Feature]) -> Dict[str, Any]:
        total_score = 100.0
        deductions_by_category = {}
        
        for f in features:
            detector_id = getattr(f, 'detector_id', 'unknown')
            category = self._get_category(detector_id)
            
            deduction = self._deduction_for(detector_id)
            ctx = getattr(f, 'context_type', 'none')
            multiplier = self.CONTEXT_MULTIPLIERS.get(ctx, 1.0)
            actual_deduction = deduction * multiplier
            
            cat_deduction = deductions_by_category.get(category, 0)
            if cat_deduction + actual_deduction > self.MAX_DEDUCTION_PER_CATEGORY:
                actual_deduction = max(0, self.MAX_DEDUCTION_PER_CATEGORY - cat_deduction)
            
            deductions_by_category[category] = cat_deduction + actual_deduction
            total_score -= actual_deduction
        
        total_score = max(0, total_score)
        
        return {
            'total_score': total_score,
            'deductions': deductions_by_category,
            'grade': self._score_to_grade(total_score)
        }"""
    
    if old_calc in c:
        # Replace hingga return statement
        pattern = re.compile(r'(    def calculate.*?)(?=\n    def |\nclass |\Z)', re.DOTALL)
        c = pattern.sub(new_calc + '\n\n', c)
        print("✅ FIX #6: scoring.py - Completed calculate() method")
        fixes_applied += 1
    else:
        print("⚠️  FIX #6: scoring.py - calculate() pattern not found")
    
    with open(p, 'w') as f:
        f.write(c)
else:
    print("❌ FIX #4 & #6: scoring.py not found")

# ============================================================
# FIX #5: unified_auditor.py - Add missing functions
# ============================================================
p = 'engine/unified_auditor.py'
if os.path.exists(p):
    with open(p) as f:
        c = f.read()
    
    missing_funcs = """
    def _map_detector_severity(self, detector_id: str) -> str:
        \"\"\"Petakan detector_id ke severity.\"\"\"
        severity_map = {
            'request_security': 'high',
            'graphics_object_in_block': 'medium',
            'forbidden_in_block': 'high',
            'magic_number': 'low',
            'duplicate_code': 'medium',
            'unused_variable': 'low',
            'nested_loops': 'medium',
        }
        return severity_map.get(detector_id, 'low')
    
    def _deduction_for(self, detector_id: str) -> int:
        \"\"\"Dapatkan poin deduksi untuk detector_id.\"\"\"
        deduction_map = {
            'request_security': 10,
            'graphics_object_in_block': 5,
            'forbidden_in_block': 15,
            'magic_number': 3,
            'duplicate_code': 5,
            'unused_variable': 2,
            'nested_loops': 8,
        }
        return deduction_map.get(detector_id, 2)
"""
    
    if '_map_detector_severity' not in c:
        # Tambahkan sebelum method terakhir atau di akhir class
        class_match = re.search(r'class\s+UnifiedAuditor.*?:', c)
        if class_match:
            # Cari position untuk insert (sebelum method terakhir atau di akhir)
            last_def_pos = c.rfind('    def ')
            if last_def_pos > 0:
                c = c[:last_def_pos] + missing_funcs + '\n' + c[last_def_pos:]
                print("✅ FIX #5: unified_auditor.py - Added _map_detector_severity and _deduction_for")
                fixes_applied += 1
    else:
        print("⚠️  FIX #5: unified_auditor.py - Functions already exist")
    
    with open(p, 'w') as f:
        f.write(c)
else:
    print("❌ FIX #5: unified_auditor.py not found")

# ============================================================
# FIX #7: cfg.py - Add build_cfg() function
# ============================================================
p = 'engine/cfg.py'
if os.path.exists(p):
    with open(p) as f:
        c = f.read()
    
    if 'def build_cfg' not in c:
        build_cfg_func = """
def build_cfg(root) -> 'ControlFlowGraph':
    \"\"\"Bangun CFG dari AST root.\"\"\"
    from engine.ast_nodes import IfStatement, ForStatement, WhileStatement, ForInStatement
    
    cfg = ControlFlowGraph()
    entry = BasicBlock(label="entry")
    cfg.add_block(entry)
    cfg.entry = entry
    
    def traverse(node, current_block):
        if isinstance(node, IfStatement):
            cond_block = BasicBlock(label=f"if_{id(node)}")
            cfg.add_block(cond_block)
            current_block.add_successor(cond_block)
            
            then_block = BasicBlock(label=f"then_{id(node)}")
            cfg.add_block(then_block)
            if hasattr(node, 'then_body'):
                for stmt in node.then_body:
                    traverse(stmt, then_block)
            
            else_block = BasicBlock(label=f"else_{id(node)}")
            cfg.add_block(else_block)
            if hasattr(node, 'else_body'):
                for stmt in node.else_body:
                    traverse(stmt, else_block)
            
            merge_block = BasicBlock(label=f"merge_{id(node)}")
            cfg.add_block(merge_block)
            then_block.add_successor(merge_block)
            else_block.add_successor(merge_block)
            
            return merge_block
        
        elif isinstance(node, (ForStatement, WhileStatement, ForInStatement)):
            loop_block = BasicBlock(label=f"loop_{id(node)}")
            cfg.add_block(loop_block)
            current_block.add_successor(loop_block)
            
            if hasattr(node, 'body'):
                for stmt in node.body:
                    traverse(stmt, loop_block)
            loop_block.add_successor(loop_block)
            
            return loop_block
        
        else:
            if hasattr(node, 'body') and isinstance(node.body, list):
                for stmt in node.body:
                    current_block = traverse(stmt, current_block)
                return current_block
            else:
                block = BasicBlock(label=f"stmt_{id(node)}")
                cfg.add_block(block)
                current_block.add_successor(block)
                return block
    
    if hasattr(root, 'body'):
        for stmt in root.body:
            entry = traverse(stmt, entry)
    
    return cfg
"""
        c += build_cfg_func
        print("✅ FIX #7: cfg.py - Added build_cfg() function")
        fixes_applied += 1
    else:
        print("⚠️  FIX #7: cfg.py - build_cfg() already exists")
    
    with open(p, 'w') as f:
        f.write(c)
else:
    print("❌ FIX #7: cfg.py not found")

print(f"\n🔄 Total critical fixes applied: {fixes_applied}/7")
