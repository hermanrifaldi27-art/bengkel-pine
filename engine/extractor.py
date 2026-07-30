#!/usr/bin/env python3
"""
PineAST Extractor v5.2 — CFG-aware, flow-sensitive, scope-safe
"""
import sys
from typing import List, Optional, Dict, Set, Any
from engine.parser import (
    ASTNode, Module,
    IntegerLiteral, FloatLiteral, StringLiteral, BoolLiteral,
    Identifier, QualifiedName, UnaryOp, BinaryOp, TernaryOp,
    Call, Index, MemberAccess, RangeExpr, TupleLiteral,
    DestructuringAssignment, GenericType, ArrowFunction, TypeField,
    VarDeclaration, ConstDeclaration, TypeDeclaration, EnumDeclaration,
    MethodDeclaration, FunctionDeclaration, ImportDeclaration,
    LibraryDeclaration, ExportDeclaration, Assignment,
    IfStatement, ForStatement, ForInStatement, WhileStatement,
    SwitchStatement, ReturnStatement, BreakStatement, ContinueStatement,
    ExpressionStatement, Directive,
    SourceSpan
)
from engine.signature import SignatureGenerator
from engine.semantic import SemanticAnalyzer, analyze as semantic_analyze
from engine.ast_utils import get_children
from engine.visitor import ASTVisitor
from engine.cfg import build_cfg, CFG, BasicBlock, LoopInfo
from engine.diagnostics import DiagnosticEngine, Diagnostic, Severity
from engine.types import TYPE_INT
from engine.evaluator import ConstantValue

class Feature:
    def __init__(self, module, goal, tactic, context, signature, detector_id, anchor=None, diagnostic=None):
        self.module = module
        self.goal = goal
        self.tactic = tactic
        self.context = context
        self.signature = signature
        self.detector_id = detector_id
        self.anchor = anchor
        self.diagnostic = diagnostic
    def __hash__(self):
        return hash((self.module, self.tactic, self.context))
    def __eq__(self, other):
        if not isinstance(other, Feature): return NotImplemented
        return (self.module == other.module and self.tactic == other.tactic and self.context == other.context)

class TraversalContext:
    def __init__(self):
        self.function_stack = []
        self.if_stack = []
        self.loop_stack = []
        self.switch_stack = []
    @property
    def in_function(self): return len(self.function_stack) > 0
    @property
    def in_if(self): return len(self.if_stack) > 0
    @property
    def in_loop(self): return len(self.loop_stack) > 0
    @property
    def in_switch(self): return len(self.switch_stack) > 0
    def push_function(self, n): self.function_stack.append(n)
    def pop_function(self): self.function_stack.pop()
    def push_if(self, n): self.if_stack.append(n)
    def pop_if(self): self.if_stack.pop()
    def push_loop(self, n): self.loop_stack.append(n)
    def pop_loop(self): self.loop_stack.pop()
    def push_switch(self, n): self.switch_stack.append(n)
    def pop_switch(self): self.switch_stack.pop()

class FeatureExtractor(ASTVisitor):
    def __init__(self, ast: Module, code: str = "", semantic: Optional[SemanticAnalyzer] = None):
        self.ast = ast
        self.code = code
        self.features: Set[Feature] = set()
        self.ctx = TraversalContext()
        self.array_info: Dict[str, Dict[str, int]] = {}
        self.matrix_info: Dict[str, Dict[str, int]] = {}
        self.semantic = semantic or semantic_analyze(ast)
        self.diagnostics = self.semantic.diagnostics
        self.cfg: Optional[CFG] = None

    def extract_all(self) -> List[Feature]:
        self.cfg = build_cfg(self.ast)
        # Analisis flow-sensitive untuk array/matrix
        if self.cfg:
            self._analyze_flow_sensitive()
        self.visit(self.ast)
        self._finalize_array_matrix()
        return list(self.features)

    def _analyze_flow_sensitive(self):
        """Analisis flow-sensitive: cek apakah eviction ada di semua path."""
        for loop in self.cfg.loops:
            # Cek apakah ada operasi shift/remove di dalam loop body
            has_eviction = False
            for block in loop.body_blocks:
                for stmt in block.statements:
                    if isinstance(stmt, ExpressionStatement):
                        if self._is_eviction_call(stmt.expression):
                            has_eviction = True
            if not has_eviction:
                # Loop tanpa eviction, cek apakah ada array.push di body
                for block in loop.body_blocks:
                    for stmt in block.statements:
                        if isinstance(stmt, ExpressionStatement):
                            if self._is_push_call(stmt.expression):
                                self._add_feature('cleanup',
                                    'Loop tanpa eviction terdeteksi untuk array push',
                                    'Tambahkan eviction (shift/pop/remove) di dalam loop',
                                    'CALCULATIONS', 'loop_no_eviction_v1')

    def _is_eviction_call(self, expr: ASTNode) -> bool:
        if isinstance(expr, Call) and isinstance(expr.func, MemberAccess):
            return expr.func.member in ('shift', 'pop', 'remove', 'remove_row', 'remove_col', 'clear')
        return False

    def _is_push_call(self, expr: ASTNode) -> bool:
        if isinstance(expr, Call) and isinstance(expr.func, MemberAccess):
            return expr.func.member in ('push', 'add_row', 'add_col')
        return False

    def _add_feature(self, module, goal, tactic, context, detector_id, anchor=None, diag_code=None, diag_msg=None, ctx_context=None):
        sig = SignatureGenerator.generate(tactic)
        if isinstance(anchor, SourceSpan):
            anchor_str = f"line {anchor.start_line}:{anchor.start_col}"
        elif isinstance(anchor, str):
            anchor_str = anchor
        else:
            anchor_str = None
        diag = None
        if diag_code:
            diag = Diagnostic(diag_code, diag_msg or goal, Severity.WARNING, anchor)
            self.diagnostics.add(diag)
        feat = Feature(module, goal, tactic, context, sig, detector_id, anchor_str, diagnostic=diag)
        if ctx_context:
            feat.ctx_context = ctx_context
        else:
            feat.ctx_context = "is_indicator"
        self.features.add(feat)

    # Visitor overrides
    def visit_FunctionDeclaration(self, node):
        self.ctx.push_function(node); self.generic_visit(node); self.ctx.pop_function()
    def visit_MethodDeclaration(self, node):
        self.ctx.push_function(node); self.generic_visit(node); self.ctx.pop_function()
    def visit_IfStatement(self, node):
        self.ctx.push_if(node); self.generic_visit(node); self.ctx.pop_if()
    def visit_ForStatement(self, node):
        self.ctx.push_loop(node); self.generic_visit(node); self.ctx.pop_loop()
    def visit_ForInStatement(self, node):
        self.ctx.push_loop(node); self.generic_visit(node); self.ctx.pop_loop()
    def visit_WhileStatement(self, node):
        self.ctx.push_loop(node); self.generic_visit(node); self.ctx.pop_loop()
    def visit_ForStatement(self, node):
        self._detect_magic_number(node)
        self.ctx.push_loop(node); self.generic_visit(node); self.ctx.pop_loop()

    def visit_WhileStatement(self, node):
        self._detect_magic_number(node)
        self.ctx.push_loop(node); self.generic_visit(node); self.ctx.pop_loop()

    def visit_SwitchStatement(self, node):
        self.ctx.push_switch(node); self.generic_visit(node); self.ctx.pop_switch()

    def _detect_unused_variable(self, node):
        """Deteksi var yang dideklarasikan tapi tidak pernah di-assign ulang."""
        if isinstance(node, VarDeclaration):
            # Cek apakah var di-assign di tempat lain (sederhana: cek apakah nama muncul setelah deklarasi)
            if node.name and not node.value:
                # Cek apakah nama var muncul di assignment di bagian kode setelah deklarasi
                rest_code = self.code.split(node.name, 1)
                if len(rest_code) > 1:
                    rest = rest_code[1]
                    # Cek apakah ada assignment ke var ini (:=  atau =)
                    import re
                    if not re.search(rf'\b{node.name}\s*:=', rest) and not re.search(rf'\b{node.name}\s*=', rest):
                        self._add_feature('state',
                            f'var {node.name} dideklarasikan tapi tidak pernah di-assign — mungkin tidak terpakai',
                            f'Hapus atau gunakan var {node.name}',
                            'STATE', 'unused_variable_v1',
                            anchor=node.span, diag_code='PINE0019')

    def visit_VarDeclaration(self, node):
        if node.value and isinstance(node.value, Identifier) and node.value.name == 'na':
            sym = self.semantic.get_symbol(node.name)
            if sym and sym.type and sym.type == TYPE_INT:
                self._add_feature('state', f"var int {node.name} = na -> ubah ke 0",
                                  f"var int {node.name} = 0", 'STATE', 'var_int_na_v1',
                                  anchor=node.span, diag_code='PINE0001')
        self._detect_unused_variable(node)
        self._collect_array_matrix_info(node)
        self.generic_visit(node)

    def visit_ReturnStatement(self, node):
        self.generic_visit(node)

    def visit_Call(self, node):
        func_name = self._get_func_name(node.func)
        # Detektor baru
        self._detect_security_in_loop(node)
        self._detect_hline_in_if(node)
        self._detect_input_type_mismatch(node)
        self._detect_redundant_plot(node)
        self._detect_lookahead_bias(node)
        # Detektor lama
        if self.ctx.in_if and not self.ctx.in_function and not self.ctx.in_loop and func_name:
            # Fungsi plotting TIDAK BOLEH di dalam if -> HARUS pindah ke global scope
            plot_names = {'plot', 'plotshape', 'plotchar', 'plotarrow', 'plotcandle', 'plotbar',
                          'hline', 'fill', 'bgcolor', 'barcolor'}
            # Fungsi objek visual BOLEH di dalam if tapi HARUS pakai var x = na di luar
            obj_names = {'line.new', 'box.new', 'label.new', 'table.new', 'polyline.new'}
            if func_name in plot_names:
                self._add_feature('plots', f'{func_name} di dalam if global -> pindahkan ke global scope',
                                  f'{func_name}(cond ? expr : na)', 'PLOTS', 'plot_in_if_v1',
                                  anchor=node.span, diag_code='PINE0003')
            elif func_name in obj_names:
                self._add_feature('objects', f'{func_name} di dalam if global -> gunakan var untuk deklarasi di luar',
                                  f'var x = {func_name.split(".")[-1]}.new(...)', 'OBJECTS', 'obj_in_if_v1',
                                  anchor=node.span, diag_code='PINE0008')
            elif func_name == 'alertcondition':
                self._add_feature('alert', 'alertcondition di dalam if global -> pindahkan',
                                  'alertcondition(cond, title, message)', 'ALERT', 'alertcondition_in_if_v1',
                                  anchor=node.span, diag_code='PINE0004')
        if func_name == 'request.security':
            self._check_request_security(node)
        # Detektor baru: box/line/linefill dalam if/loop
        self._detect_drawing_in_loop(node)
        self._detect_rebuild_in_islast(node)
        self._collect_array_matrix_call(node)
        self.generic_visit(node)

    def _check_request_security(self, node: Call):
        has_valid = False
        for arg in node.args:
            if isinstance(arg, Assignment) and isinstance(arg.target, Identifier) and arg.target.name == 'lookahead':
                scope = self.semantic.get_scope_of(arg)
                val = self.semantic.evaluate_constant(arg.value, scope)
                actual_val = None
                if isinstance(val, ConstantValue):
                    actual_val = str(val.value)
                elif hasattr(val, 'value'):
                    actual_val = str(val.value)
                elif isinstance(val, str):
                    actual_val = val
                if actual_val and 'lookahead_off' in actual_val:
                    has_valid = True
            # Juga cek parameter gaps
            has_gaps = False
            for arg in node.args:
                if isinstance(arg, Assignment) and isinstance(arg.target, Identifier) and arg.target.name == 'gaps':
                    val = self.semantic.evaluate_constant(arg.value)
                    actual_val = str(val.value) if hasattr(val, 'value') else str(val)
                    if 'gaps_off' in actual_val:
                        has_gaps = True
            if not has_valid and not has_gaps:
                self._add_feature('data_fetching',
                    'request.security tanpa lookahead dan gaps — tambahkan gaps=barmerge.gaps_off',
                    'request.security(..., gaps = barmerge.gaps_off)',
                    'DATA_FETCHING', 'security_gaps_v1',
                    anchor=node.span, diag_code='PINE0017')
        if not has_valid:
            self._add_feature('data_fetching', 'request.security tanpa lookahead_off -> tambahkan',
                              'request.security(..., lookahead = barmerge.lookahead_off)',
                              'DATA_FETCHING', 'request_security_lookahead_v1',
                              anchor=node.span, diag_code='PINE0005')


    def _detect_security_in_loop(self, node: Call):
        """Deteksi request.security() di dalam loop."""
        func_name = self._get_func_name(node.func)
        if func_name in ('request.security', 'request.security_lower_tf') and self.ctx.in_loop:
            self._add_feature('data_fetching',
                f'{func_name} di dalam loop -> pindahkan ke luar loop dengan var cache',
                f'var cached = {func_name}(...)\nfor ...\n    use cached',
                'DATA_FETCHING', 'security_in_loop_v1',
                anchor=node.span, diag_code='PINE0009')

    def _detect_hline_in_if(self, node: Call):
        """Deteksi hline() di dalam if global."""
        func_name = self._get_func_name(node.func)
        if func_name == 'hline' and self.ctx.in_if and not self.ctx.in_function and not self.ctx.in_loop:
            self._add_feature('plots',
                'hline di dalam if global -> pindahkan ke global scope',
                'hline(price, title, color, linestyle, linewidth)',
                'PLOTS', 'hline_in_if_v1',
                anchor=node.span, diag_code='PINE0010')

    def _detect_input_type_mismatch(self, node: Call):
        """Deteksi input.int(defval=3.14) — tipe tidak cocok."""
        func_name = self._get_func_name(node.func)
        if func_name == 'input.int' and node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, (FloatLiteral,)):
                self._add_feature('inputs',
                    'input.int dengan defval float -> gunakan input.float',
                    'input.float(defval=...)',
                    'INPUTS', 'input_type_mismatch_v1',
                    anchor=node.span, diag_code='PINE0011')

    def _detect_strategy_in_indicator(self, node: Call):
        """Deteksi strategy.* di indicator()."""
        func_name = self._get_func_name(node.func)
        strategy_funcs = {'strategy.entry', 'strategy.exit', 'strategy.close', 'strategy.close_all',
                          'strategy.order', 'strategy.cancel', 'strategy.cancel_all'}
        if func_name in strategy_funcs:
            # Cek apakah ada indicator() di global functions
            if 'indicator' in self.semantic.get_all_symbols_of_kind('function') if hasattr(self.semantic, 'get_all_symbols_of_kind') else False:
                pass  # Tidak bisa cek dari sini, perlu akses ke AST root
            self._add_feature('strategy',
                f'{func_name} terdeteksi -> pastikan skrip adalah strategy, bukan indicator',
                f'Ganti indicator() menjadi strategy()',
                'STRATEGY', 'strategy_in_indicator_v1',
                anchor=node.span, diag_code='PINE0012')

    def _detect_redundant_plot(self, node: Call):
        """Deteksi plot dengan argumen literal yang tidak berubah."""
        func_name = self._get_func_name(node.func)
        if func_name == 'plot' and node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, (IntegerLiteral, FloatLiteral)):
                self._add_feature('plots',
                    'plot dengan nilai literal statis -> tidak akan berubah, mungkin tidak diperlukan',
                    'Gunakan series yang dinamis',
                    'PLOTS', 'redundant_plot_v1',
                    anchor=node.span, diag_code='PINE0013')

    def _detect_magic_number(self, node):
        """Deteksi angka literal yang muncul di loop/condition tanpa konstanta (magic number)."""
        from engine.parser import ForStatement, WhileStatement, IntegerLiteral, FloatLiteral
        if isinstance(node, (ForStatement, WhileStatement)):
            def check_magic(n):
                if isinstance(n, (IntegerLiteral, FloatLiteral)):
                    val = n.value
                    if isinstance(val, int) and val not in (0, 1, -1, 2) and val > 3:
                        self._add_feature('style',
                            f'Magic number {val} terdeteksi di loop — gunakan konstanta bernama',
                            f'const LENGTH = {val}',
                            'STYLE', 'magic_number_v1',
                            anchor=n.span, diag_code='PINE0016')
                if hasattr(n, 'left'): check_magic(n.left)
                if hasattr(n, 'right'): check_magic(n.right)
                if hasattr(n, 'operand'): check_magic(n.operand)
            if hasattr(node, 'iterable'):
                check_magic(node.iterable)

    def _detect_lookahead_bias(self, node: Call):
        """Deteksi request.security dengan lookahead_on."""
        func_name = self._get_func_name(node.func)
        if func_name == 'request.security':
            for arg in node.args:
                if isinstance(arg, Assignment) and isinstance(arg.target, Identifier) and arg.target.name == 'lookahead':
                    val = self.semantic.evaluate_constant(arg.value)
                    actual_val = str(val.value) if hasattr(val, 'value') else str(val)
                    if 'lookahead_on' in actual_val:
                        self._add_feature('data_fetching',
                            'request.security dengan lookahead_on -> bias future, gunakan lookahead_off',
                            'lookahead = barmerge.lookahead_off',
                            'DATA_FETCHING', 'lookahead_bias_v1',
                            anchor=node.span, diag_code='PINE0014')

    def _detect_var_unused(self, node: VarDeclaration):
        """Deteksi var yang tidak pernah di-assign ulang (hanya deklarasi)."""
        if node.name and not node.value:
            # Cek apakah var ini pernah di-assign di tempat lain
            # Sederhana: cek apakah nama var muncul di assignment di kode
            if node.name not in self.code:
                pass  # Tidak bisa deteksi tanpa analisis lebih dalam

    def _detect_drawing_in_loop(self, node: Call):
        """Deteksi box.new/line.new/linefill.new di dalam if/loop."""
        func_name = self._get_func_name(node.func)
        drawing_funcs = {'box.new', 'line.new', 'linefill.new'}
        if func_name in drawing_funcs and (self.ctx.in_if or self.ctx.in_loop):
            msg = func_name + ' di dalam if/loop -> gunakan var'
            fix = 'var obj = ' + func_name + '(...)'
            self._add_feature('objects', msg, fix,
                'OBJECTS', 'drawing_in_loop_v1',
                anchor=node.span, diag_code='PINE0015')

    def _detect_rebuild_in_islast(self, node):
        """Deteksi penghancuran & pembuatan ulang objek di barstate.islast (anti-pattern)."""
        if isinstance(node, Call):
            func_name = self._get_func_name(node.func)
            # Deteksi pola: .delete() atau .clear() — kemungkinan rebuild
            if func_name and ('.delete' in func_name or '.clear' in func_name):
                if self.ctx.in_if or self.ctx.in_loop:
                    self._add_feature('memory',
                        f'{func_name} di dalam if/loop — kemungkinan rebuild, gunakan var dan update saja',
                        'var obj = ...; if condition obj.set_*(...)',
                        'MEMORY', 'rebuild_in_islast_v1',
                        anchor=node.span, diag_code='PINE0018')

    def _get_context(self) -> str:
        """Konteks saat ini: in_loop / in_if / in_function / is_indicator"""
        if self.ctx.in_loop:
            return "in_loop"
        if self.ctx.in_if:
            return "in_if"
        if self.ctx.in_function:
            return "in_function"
        return "is_indicator"

    def _get_func_name(self, node):
        if isinstance(node, Identifier): return node.name
        elif isinstance(node, QualifiedName): return '.'.join(node.parts)
        elif isinstance(node, MemberAccess):
            target = self._get_func_name(node.target)
            if target: return f"{target}.{node.member}"
        return None

    def _collect_array_matrix_info(self, node):
        if node.type and isinstance(node.type, GenericType):
            if node.type.base == 'array':
                self.array_info[node.name] = {'push':0, 'shift':0, 'pop':0, 'remove':0, 'clear':0}
            elif node.type.base == 'matrix':
                self.matrix_info[node.name] = {'add_row':0, 'remove_row':0, 'remove_col':0, 'clear':0}
        if node.value and isinstance(node.value, Call):
            f = node.value.func
            if isinstance(f, QualifiedName):
                if f.parts == ['array', 'new']:
                    self.array_info[node.name] = self.array_info.get(node.name, {'push':0, 'shift':0, 'pop':0, 'remove':0, 'clear':0})
                elif f.parts == ['matrix', 'new']:
                    self.matrix_info[node.name] = self.matrix_info.get(node.name, {'add_row':0, 'remove_row':0, 'remove_col':0, 'clear':0})

    def _collect_array_matrix_call(self, node):
        func = node.func
        if isinstance(func, MemberAccess) and isinstance(func.target, Identifier):
            nm = func.target.name
            if nm in self.array_info and func.member in self.array_info[nm]:
                self.array_info[nm][func.member] += 1
            if nm in self.matrix_info and func.member in self.matrix_info[nm]:
                self.matrix_info[nm][func.member] += 1

    def _finalize_array_matrix(self):
        # Flow-sensitive: hanya laporkan jika push > 0 DAN tidak ada eviction di SEMUA path
        for name, info in self.array_info.items():
            if info['push'] > 0:
                has_eviction = info['shift'] > 0 or info['pop'] > 0 or info['remove'] > 0 or info['clear'] > 0
                # Cek CFG: apakah eviction ada di semua path setelah push?
                if self.cfg:
                    flow_safe = self._check_eviction_in_all_paths(name, 'array')
                    if flow_safe:
                        has_eviction = True
                if not has_eviction:
                    self._add_feature('cleanup', f"Array `{name}` unbounded -> tambahkan eviction",
                                      f"while array.size({name}) > limit\n    array.shift({name})",
                                      'CALCULATIONS', 'array_unbounded_v1', anchor=f"array.push({name})", diag_code='PINE0006')
        for name, info in self.matrix_info.items():
            if info['add_row'] > 0:
                has_eviction = info['remove_row'] > 0 or info['remove_col'] > 0 or info['clear'] > 0
                if self.cfg:
                    flow_safe = self._check_eviction_in_all_paths(name, 'matrix')
                    if flow_safe:
                        has_eviction = True
                if not has_eviction:
                    self._add_feature('cleanup', f"Matrix `{name}` unbounded -> tambahkan eviction",
                                      f"if matrix.rows({name}) > limit\n    matrix.remove_row({name}, matrix.rows({name}) - 1)",
                                      'CALCULATIONS', 'matrix_unbounded_v1', anchor=f"matrix.add_row({name})", diag_code='PINE0007')

    def _check_eviction_in_all_paths(self, name: str, kind: str) -> bool:
        """Cek apakah eviction ada di semua path setelah push (flow-sensitive)."""
        if not self.cfg:
            return False
        # Sederhana: cek apakah ada eviction call di blok yang sama atau setelah push
        for block in self.cfg.blocks:
            for stmt in block.statements:
                if isinstance(stmt, ExpressionStatement):
                    expr = stmt.expression
                    if isinstance(expr, Call) and isinstance(expr.func, MemberAccess):
                        if expr.func.target and hasattr(expr.func.target, 'name') and expr.func.target.name == name:
                            if kind == 'array' and expr.func.member in ('shift', 'pop', 'remove', 'clear'):
                                return True
                            if kind == 'matrix' and expr.func.member in ('remove_row', 'remove_col', 'clear'):
                                return True
        return False

def extract_features(file_path: str) -> Optional[List[Feature]]:
    from engine.parser import PineAST
    try:
        with open(file_path, 'r') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"❌ File tidak ditemukan: {file_path}")
        return None
    except Exception as e:
        print(f"❌ Error membaca file: {e}")
        return None
    try:
        ast_obj = PineAST(code)
    except SyntaxError as e:
        print(f"❌ Error parsing: {e}")
        return None
    except Exception as e:
        print(f"❌ Error tidak terduga: {e}")
        return None
    extractor = FeatureExtractor(ast_obj.root, code)
    features = extractor.extract_all()
    return features

def run_extract(file_path: str, dry_run: bool = True):
    features = extract_features(file_path)
    if features is None:
        return
    if not features:
        print("ℹ️ Tidak ada pola ditemukan.")
        return
    print(f"📊 Ditemukan {len(features)} fitur:")
    for f in features:
        print(f"   - {f.module}: {f.goal} ({f.signature})")
    if not dry_run:
        from engine.contract_writer import ContractWriter
        for f in features:
            ContractWriter.write_rule(f, dry_run=False)
        print("✅ Kontrak ditulis.")
    else:
        print("ℹ️ Dry-run: kontrak tidak ditulis.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 -m engine.extractor <file.pine>")
        sys.exit(1)
    run_extract(sys.argv[1], dry_run=True)
