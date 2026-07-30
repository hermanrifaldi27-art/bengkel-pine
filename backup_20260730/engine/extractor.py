import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class Feature:
    module: str
    goal: str
    tactic: str
    context: str
    signature: str
    detector_id: str

class FeatureExtractor:
    def __init__(self, ast):
        self.ast = ast
        self.code = ast.code  # fallback
        self.features = []
    
    def extract_all(self) -> List[Feature]:
        """Ekstrak semua fitur dari AST"""
        # 🔥 Detektor berbasis AST (prioritas utama)
        self._detect_udt_from_ast()
        self._detect_method_from_ast()
        self._detect_barstate_from_ast()
        self._detect_request_security_from_ast()
        
        # 🔥 Fallback: regex (untuk pola yang belum di-cover AST)
        self._detect_plot_in_if_regex()
        self._detect_enum_from_ast()
        self._detect_lower_tf_from_ast()
        self._detect_box_with_text_align()
        self._detect_enum_from_ast()
        self._detect_switch_from_ast()
        self._detect_array_ops_from_ast()
        self._detect_color_gradient_from_ast()
        self._detect_enum_from_ast()
        self._detect_switch_from_ast()
        self._detect_array_ops_from_ast()
        self._detect_math_ops()
        self._detect_enum_from_ast()
        self._detect_array_ops_from_ast()
        self._detect_box_transparent()
        self._detect_var_in_function_regex()
        
        return self.features
    
    def _add_feature(self, module: str, goal: str, tactic: str, context: str, detector_id: str):
        from engine.signature import SignatureGenerator
        sig = SignatureGenerator.generate(tactic)
        self.features.append(Feature(
            module=module,
            goal=goal,
            tactic=tactic,
            context=context,
            signature=sig,
            detector_id=detector_id
        ))
    
    # ─── AST-BASED DETEKTOR ──────────────────────────────
    def _detect_udt_from_ast(self):
        """Deteksi UDT dari AST (type, enum)"""
        # Gunakan regex dulu, nanti upgrade ke AST murni
        for match in re.finditer(r'(type\s+(\w+)\s*\{[^}]*\})', self.code, re.DOTALL):
            self._add_feature('types', f"User-Defined Type: {match.group(2)}", 
                            match.group(1), 'TYPES', 'udt_ast_v1')
        for match in re.finditer(r'(enum\s+(\w+)\s*\{[^}]*\})', self.code, re.DOTALL):
            self._add_feature('types', f"Enum: {match.group(2)}", 
                            match.group(1), 'TYPES', 'enum_ast_v1')
    
    def _detect_method_from_ast(self):
        """Deteksi method dari AST"""
        for match in re.finditer(r'(method\s+\w+\s*\([^)]*\)\s*=>\s*\{[^}]*\})', self.code, re.DOTALL):
            self._add_feature('functions', 'Method declaration', 
                            match.group(1), 'FUNCTIONS', 'method_ast_v1')
    
    def _detect_barstate_from_ast(self):
        """Deteksi barstate.isfirst / barstate.islast"""
        if 'barstate.isfirst' in self.code:
            self._add_feature('lifecycle', 'Inisialisasi di barstate.isfirst', 
                            'if barstate.isfirst\n    ...', 'LIFECYCLE', 'barstate_first_v1')
        if 'barstate.islast' in self.code:
            self._add_feature('lifecycle', 'Eksekusi di barstate.islast', 
                            'if barstate.islast\n    ...', 'LIFECYCLE', 'barstate_last_v1')
    
    def _detect_request_security_from_ast(self):
        """Deteksi request.security"""
        for match in re.finditer(r'(request\.security\([^)]+\))', self.code):
            self._add_feature('data_fetching', 'request.security untuk higher timeframe', 
                            match.group(1), 'DATA_FETCHING', 'request_security_ast_v1')
    
    # ─── REGEX FALLBACK ──────────────────────────────────
    def _detect_plot_in_if_regex(self):
        """Fallback: plot di dalam if"""
        for match in re.finditer(r'if\s+[^:]*:\s*\n\s*(plot\s*\([^)]+\))', self.code, re.MULTILINE):
            self._add_feature('plots', 'plot di dalam if (harus pindah ke global)', 
                            match.group(1), 'PLOTS', 'plot_in_if_regex_v1')
    
    def _detect_var_in_function_regex(self):
        """Fallback: var di dalam fungsi"""
        for match in re.finditer(r'(function\s+\w+\s*\([^)]*\)\s*=>\s*\{[^}]*\bvar\b[^}]*\})', self.code, re.DOTALL):
            self._add_feature('functions', 'var di dalam fungsi (harus pindah ke STATE)', 
                            match.group(1), 'FUNCTIONS', 'var_in_function_regex_v1')
    def _detect_enum_from_ast(self):
        """Deteksi enum (Pine Script v6)"""
        for match in re.finditer(r'(enum\s+(\w+)\s*\{[^}]*\})', self.code, re.DOTALL):
            self._add_feature('types', f"Enum: {match.group(2)}", 
                            match.group(1), 'TYPES', 'enum_ast_v2')
    
    def _detect_lower_tf_from_ast(self):
        """Deteksi request.security_lower_tf"""
        for match in re.finditer(r'(request\.security_lower_tf\([^)]+\))', self.code):
            self._add_feature('data_fetching', 'request.security_lower_tf untuk lower timeframe', 
                            match.group(1), 'DATA_FETCHING', 'lower_tf_ast_v1')
    
    def _detect_box_with_text_align(self):
        """Deteksi box.new dengan text_halign / text_valign"""
        for match in re.finditer(r'(box\.new\([^)]*text_halign[^)]*\))', self.code, re.DOTALL):
            self._add_feature('drawings', 'Box dengan text alignment', 
                            match.group(1), 'DRAWINGS', 'box_text_align_v1')
    def _detect_enum_from_ast(self):
        """Deteksi enum (Pine Script v6)"""
        for match in re.finditer(r'(enum\s+(\w+)\s*\{[^}]*\})', self.code, re.DOTALL):
            self._add_feature('types', f"Enum: {match.group(2)}", 
                            match.group(1), 'TYPES', 'enum_ast_v2')
    def _detect_switch_from_ast(self):
        """Deteksi switch statement"""
        for match in re.finditer(r'(switch\s+[^{]*\{[^}]*\})', self.code, re.DOTALL):
            self._add_feature('functions', 'Switch statement', 
                            match.group(1), 'FUNCTIONS', 'switch_ast_v1')
    def _detect_array_ops_from_ast(self):
        """Deteksi array.set, array.get, array.push"""
        for match in re.finditer(r'(array\.(set|get|push)\([^)]+\))', self.code):
            self._add_feature('calculations', 'Array manipulation', 
                            match.group(1), 'CALCULATIONS', 'array_ops_ast_v1')
    def _detect_color_gradient_from_ast(self):
        """Deteksi color.from_gradient"""
        for match in re.finditer(r'(color\.from_gradient\([^)]+\))', self.code):
            self._add_feature('plots', 'Warna gradien', 
                            match.group(1), 'PLOTS', 'gradient_ast_v1')
    def _detect_enum_from_ast(self):
        """Deteksi enum menggunakan AST (symbols)"""
        # Dari PineAST, kita bisa dapatkan symbols, tapi enum belum terdeteksi.
        # Kita tetap pakai regex tapi lebih fleksibel.
        for match in re.finditer(r'(enum\s+(\w+)\s*\{[^}]*\})', self.code, re.DOTALL):
            self._add_feature('types', f"Enum: {match.group(2)}", 
                            match.group(1), 'TYPES', 'enum_ast_v2')
    def _detect_switch_from_ast(self):
        """Deteksi switch statement (lebih fleksibel)"""
        # Cari switch dengan atau tanpa kurung kurawal
        for match in re.finditer(r'(switch\s+[^{]*\{[^}]*\})', self.code, re.DOTALL):
            self._add_feature('functions', 'Switch statement', 
                            match.group(1), 'FUNCTIONS', 'switch_ast_v1')
        # Cari switch yang tidak pakai kurung kurawal (misal switch x)
        for match in re.finditer(r'(switch\s+[^;{]+)', self.code):
            self._add_feature('functions', 'Switch statement (inline)', 
                            match.group(1), 'FUNCTIONS', 'switch_inline_v1')
    def _detect_array_ops_from_ast(self):
        """Deteksi array.set, array.get, array.push dengan spasi fleksibel"""
        for match in re.finditer(r'(array\s*\.\s*(?:set|get|push)\s*\([^)]+\))', self.code, re.DOTALL):
            self._add_feature('calculations', 'Array manipulation', 
                            match.group(1), 'CALCULATIONS', 'array_ops_ast_v2')
    def _detect_math_ops(self):
        """Deteksi math.sign, math.abs, math.round"""
        for match in re.finditer(r'(math\.(sign|abs|round|max|min)\([^)]+\))', self.code):
            self._add_feature('calculations', 'Math operation', 
                            match.group(1), 'CALCULATIONS', 'math_ops_v1')
    def _detect_enum_from_ast(self):
        """Deteksi enum menggunakan AST (lebih akurat)"""
        # Cari enum dengan format: enum name { ... }
        for match in re.finditer(r'(enum\s+(\w+)\s*\{[^}]*\})', self.code, re.DOTALL):
            self._add_feature('types', f"Enum: {match.group(2)}", 
                            match.group(1), 'TYPES', 'enum_ast_v3')
        # Cari enum dengan format: enum name { ... } (dengan spasi ekstra)
        for match in re.finditer(r'(enum\s+(\w+)\s*\{\s*[^}]*\s*\})', self.code, re.DOTALL):
            self._add_feature('types', f"Enum: {match.group(2)}", 
                            match.group(1), 'TYPES', 'enum_ast_v3_flex')
    def _detect_array_ops_from_ast(self):
        """Deteksi array.set, array.get, array.push dengan spasi fleksibel"""
        # Cari array.set, array.get, array.push dengan spasi opsional
        for match in re.finditer(r'(array\s*\.\s*(?:set|get|push)\s*\([^)]*\))', self.code, re.DOTALL):
            self._add_feature('calculations', 'Array manipulation', 
                            match.group(1), 'CALCULATIONS', 'array_ops_ast_v3')
    def _detect_box_transparent(self):
        """Deteksi box.new dengan bgcolor transparan"""
        for match in re.finditer(r'(box\.new\([^)]*bgcolor\s*=\s*#00000000[^)]*\))', self.code, re.DOTALL):
            self._add_feature('drawings', 'Box dengan background transparan', 
                            match.group(1), 'DRAWINGS', 'box_transparent_v1')
    def _detect_math_ops(self):
        """Deteksi math.sign, math.abs, math.round, math.max, math.min — hanya 1 pola per tipe"""
        ops = ['sign', 'abs', 'round', 'max', 'min']
        for op in ops:
            if re.search(rf'math\.{op}\s*\(', self.code):
                self._add_feature('calculations', f'Math operation: {op}', 
                                f'math.{op}(...)', 'CALCULATIONS', f'math_{op}_v1')

# ─── BACKWARD COMPATIBILITY: extract_features untuk cli.py ───
def extract_features(file_path: str):
    """Wrapper untuk CLI — gunakan arsitektur baru."""
    print(f"🔍 Menganalisis {file_path} dengan AST v2.1...")
    with open(file_path, 'r') as f:
        code = f.read()
    
    from engine.parser import PineAST
    from engine.contract_writer import ContractWriter
    
    ast = PineAST(code)
    extractor = FeatureExtractor(ast)
    features = extractor.extract_all()
    
    if not features:
        print("   ℹ️ Tidak ada pola yang terdeteksi.")
        return
    
    print(f"   📊 Ditemukan {len(features)} fitur.")
    for f in features:
        print(f"  - {f.module}: {f.goal} ({f.signature})")
        ContractWriter.write_rule(f, dry_run=False)
    
    print("✅ Ekstraksi selesai.")
