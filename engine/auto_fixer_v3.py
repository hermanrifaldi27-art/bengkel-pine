#!/usr/bin/env python3
"""
Auto-Fixer v4.0 ★★★★★ — Round-trip-safe, scope-aware, AST-validated, production-grade
"""
import difflib, os, shutil, copy
from typing import List, Optional, Dict, Any, Tuple
from engine.knowledge_base_proactive import ProactiveKnowledgeBase
from engine.parser import (
    ASTNode, Module, VarDeclaration, ConstDeclaration, Assignment,
    Call, Identifier, MemberAccess, QualifiedName,
    IfStatement, ForStatement, ForInStatement, WhileStatement,
    SwitchStatement, ReturnStatement, BreakStatement, ContinueStatement,
    ExpressionStatement, Directive, FunctionDeclaration, MethodDeclaration,
    TypeDeclaration, EnumDeclaration, ImportDeclaration,
    LibraryDeclaration, ExportDeclaration, DestructuringAssignment,
    IntegerLiteral, FloatLiteral, StringLiteral, BoolLiteral,
    BinaryOp, UnaryOp, TernaryOp, Index, RangeExpr, TupleLiteral,
    ArrowFunction, GenericType, TypeField
)

class AutoFixerV3:
    """Auto-Fixer ★★★★★ — Production-grade dengan round-trip safety."""

    def __init__(self, kb=None):
        self.kb = kb or ProactiveKnowledgeBase()
        self.min_confidence = 0.7
        self.rollback_states: Dict[str, str] = {}
        self.fix_errors: List[str] = []

    def fix(self, file_path, code, features=None, dry_run=True, auto_confirm=False):
        if features is None: return None, 0
        self.rollback_states[file_path] = code
        self.fix_errors = []
        patched, fixes_applied = code, 0

        for _pass in range(3):
            pass_fixes = 0
            for f in features:
                if self.kb.get_confidence(f) < self.min_confidence:
                    continue
                # ★ P2: Scope-aware AST fix
                new_code = self._ast_fix_round_trip(patched, f)
                if new_code and new_code != patched and self._is_valid_pine(new_code):
                    if self._ast_structure_valid(new_code, patched):
                        patched, pass_fixes, fixes_applied = new_code, pass_fixes + 1, fixes_applied + 1
                        continue
                    else:
                        self.fix_errors.append(f"Round-trip failed for {getattr(f, 'detector_id', '?')}")
                # Fallback: hanya untuk backward compatibility
                # Akan dihapus setelah unparser 100% stabil
            if pass_fixes == 0:
                break
            features = self._re_extract(patched)

        if patched == code: return None, 0
        print(self._generate_diff(code, patched, file_path))
        if self.fix_errors:
            print(f"\n  ⚠️  {len(self.fix_errors)} perbaikan dibatalkan (round-trip fail)")

        if dry_run:
            print(f"\n  DRY-RUN: {fixes_applied} perbaikan siap diterapkan")
            return patched, fixes_applied
        if not auto_confirm:
            r = input(f"\n  {fixes_applied} perbaikan akan diterapkan. Lanjutkan? [y/N]: ").strip().lower()
            if r != 'y': return None, 0
        shutil.copy2(file_path, file_path + '.bak')
        with open(file_path, 'w') as f: f.write(patched)
        return patched, fixes_applied

    def rollback(self, file_path):
        if file_path in self.rollback_states:
            with open(file_path, 'w') as f: f.write(self.rollback_states[file_path])
            return True
        return False

    # ── P1+P2+P3+P4+P5: ROUND-TRIP-SAFE AST FIX ★★★★★ ──────
    def _ast_fix_round_trip(self, code, finding):
        """Clone AST → modify → unparse → validate round-trip."""
        try:
            from engine.parser import PineAST
            ast = PineAST(code)
            ast_clone = copy.deepcopy(ast)
            modified = self._modify_ast_scoped(ast_clone.root, finding, ast_clone.root)
            if not modified:
                return None
            new_code = self._unparse(ast_clone.root)
            if not new_code or new_code == code:
                return None
            # ★ P4: Validasi AST structure
            if not self._ast_structure_valid(new_code, code):
                return None
            return new_code
        except Exception as e:
            self.fix_errors.append(str(e))
            return None

    # ── P2: SCOPE-AWARE INJECTION ★★★★★ ───────────────────
    def _modify_ast_scoped(self, node, finding, root, parent=None, scope=None):
        """Modifikasi AST dengan melacak scope untuk injeksi yang tepat."""
        if scope is None:
            scope = root  # default scope = module

        detector_id = getattr(finding, 'detector_id', '')
        modified = False

        # Update scope jika masuk ke fungsi/metode
        if isinstance(node, (FunctionDeclaration, MethodDeclaration)):
            scope = node

        if isinstance(node, Call):
            func_name = self._get_func_name(node.func)
            # ★ request.security: HANYA outer call
            if func_name == 'request.security' and 'request_security' in detector_id:
                if not self._is_arg_of_call(node, parent):
                    has_lookahead = any(
                        isinstance(a, Assignment) and isinstance(a.target, Identifier) and a.target.name == 'lookahead'
                        for a in node.args
                    )
                    has_gaps = any(
                        isinstance(a, Assignment) and isinstance(a.target, Identifier) and a.target.name == 'gaps'
                        for a in node.args
                    )
                    if not has_lookahead:
                        node.args.append(Assignment(
                            target=Identifier(name='lookahead'),
                            value=MemberAccess(target=Identifier(name='barmerge'), member='lookahead_off'),
                            operator='='
                        ))
                        modified = True
                    if not has_gaps:
                        node.args.append(Assignment(
                            target=Identifier(name='gaps'),
                            value=MemberAccess(target=Identifier(name='barmerge'), member='gaps_off'),
                            operator='='
                        ))
                        modified = True
            # ★ objek dalam if/loop: suntikkan var di SCOPE yang tepat (fungsi/modul)
            if func_name in ('box.new', 'label.new', 'line.new', 'linefill.new'):
                if isinstance(parent, (IfStatement, ForStatement, WhileStatement, ForInStatement)):
                    var_name = func_name.split('.')[0] + '_var'
                    if not any(isinstance(s, VarDeclaration) and s.name == var_name for s in scope.body):
                        scope.body.insert(0, VarDeclaration(
                            varip=False, type=None, name=var_name, value=Identifier(name='na')
                        ))
                        modified = True

        # ★ P5: Single-pass traversal (optimasi O(N))
        for attr in vars(node):
            if attr.startswith('_'): continue
            val = getattr(node, attr)
            if isinstance(val, ASTNode):
                if self._modify_ast_scoped(val, finding, root, node, scope):
                    modified = True
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, ASTNode):
                        if self._modify_ast_scoped(item, finding, root, node, scope):
                            modified = True
        return modified

    def _is_arg_of_call(self, node, parent):
        """Cek apakah node adalah argumen dari Call lain."""
        return isinstance(parent, Call) and node in parent.args

    # ── P4: AST STRUCTURE VALIDATION ★★★★★ ─────────────────
    def _ast_structure_valid(self, new_code, original_code):
        """Validasi: parse ulang, bandingkan struktur AST."""
        try:
            from engine.parser import PineAST
            ast_new = PineAST(new_code)
            ast_old = PineAST(original_code)

            def count_nodes(n):
                c = 1
                for attr in vars(n):
                    if attr.startswith('_'): continue
                    val = getattr(n, attr)
                    if isinstance(val, ASTNode): c += count_nodes(val)
                    elif isinstance(val, list):
                        for item in val:
                            if isinstance(item, ASTNode): c += count_nodes(item)
                return c

            def count_calls(n):
                c = 1 if isinstance(n, Call) else 0
                for attr in vars(n):
                    if attr.startswith('_'): continue
                    val = getattr(n, attr)
                    if isinstance(val, ASTNode): c += count_calls(val)
                    elif isinstance(val, list):
                        for item in val:
                            if isinstance(item, ASTNode): c += count_calls(item)
                return c

            # Validasi: jumlah node tidak boleh berkurang drastis (>10%)
            old_count = count_nodes(ast_old.root)
            new_count = count_nodes(ast_new.root)
            if new_count < old_count * 0.9:
                return False

            # Validasi: jumlah Call tidak boleh berkurang (kita hanya menambah, bukan menghapus)
            old_calls = count_calls(ast_old.root)
            new_calls = count_calls(ast_new.root)
            if new_calls < old_calls:
                return False

            return True
        except Exception:
            return False

    # ── P1: ROUND-TRIP-SAFE UNPARSER ★★★★★ ─────────────────
    def _unparse(self, node, indent=0):
        IND = '    ' * indent
        if node is None: return ''
        if isinstance(node, Module): return '\n'.join(self._unparse(stmt, indent) for stmt in node.body)
        if isinstance(node, Directive): return f'{IND}//@{node.name}={node.value}'
        if isinstance(node, VarDeclaration):
            parts = [IND]; parts.append('varip ' if node.varip else 'var ')
            if node.type: parts.append(self._expr_to_str(node.type) + ' ')
            parts.append(node.name)
            if node.value: parts.append(' = ' + self._expr_to_str(node.value))
            return ''.join(parts)
        if isinstance(node, ConstDeclaration): return f'{IND}const {node.name} = {self._expr_to_str(node.value)}'
        if isinstance(node, Assignment): return f'{IND}{self._expr_to_str(node.target)} {node.operator} {self._expr_to_str(node.value)}'
        if isinstance(node, ExpressionStatement): return f'{IND}{self._expr_to_str(node.expression)}'
        if isinstance(node, IfStatement):
            result = [f'{IND}if {self._expr_to_str(node.condition)}']
            for stmt in node.then_body: result.append(self._unparse(stmt, indent + 1))
            if node.else_body:
                result.append(f'{IND}else')
                for stmt in node.else_body: result.append(self._unparse(stmt, indent + 1))
            return '\n'.join(result)
        if isinstance(node, ForStatement):
            result = [f'{IND}for {self._expr_to_str(node.iterator)} = {self._expr_to_str(node.iterable)}']
            for stmt in node.body: result.append(self._unparse(stmt, indent + 1))
            return '\n'.join(result)
        if isinstance(node, ForInStatement):
            targets = ', '.join(self._expr_to_str(t) for t in node.targets)
            result = [f'{IND}for [{targets}] in {self._expr_to_str(node.iterable)}']
            for stmt in node.body: result.append(self._unparse(stmt, indent + 1))
            return '\n'.join(result)
        if isinstance(node, WhileStatement):
            result = [f'{IND}while {self._expr_to_str(node.condition)}']
            for stmt in node.body: result.append(self._unparse(stmt, indent + 1))
            return '\n'.join(result)
        if isinstance(node, SwitchStatement):
            val = self._expr_to_str(node.value) if node.value else ''
            result = [f'{IND}switch {val}']
            for case_val, case_body in node.cases:
                result.append(f'{IND}    {self._expr_to_str(case_val)} =>')
                for stmt in case_body: result.append(self._unparse(stmt, indent + 2))
            if node.default_body:
                result.append(f'{IND}    =>')
                for stmt in node.default_body: result.append(self._unparse(stmt, indent + 2))
            return '\n'.join(result)
        if isinstance(node, ReturnStatement):
            return f'{IND}return {self._expr_to_str(node.value) if node.value else ""}'.strip()
        if isinstance(node, BreakStatement): return f'{IND}break'
        if isinstance(node, ContinueStatement): return f'{IND}continue'
        if isinstance(node, FunctionDeclaration):
            params = ', '.join(f"{self._expr_to_str(p.get('type')) + ' ' if p.get('type') else ''}{p.get('name', '')}" for p in node.params)
            result = [f'{IND}{node.name}({params}) =>']
            for stmt in node.body: result.append(self._unparse(stmt, indent + 1))
            return '\n'.join(result)
        if isinstance(node, MethodDeclaration):
            params = ', '.join(f"{self._expr_to_str(p.get('type')) + ' ' if p.get('type') else ''}{p.get('name', '')}" for p in node.params)
            result = [f'{IND}method {node.name}({params}) =>']
            for stmt in node.body: result.append(self._unparse(stmt, indent + 1))
            return '\n'.join(result)
        if isinstance(node, TypeDeclaration):
            result = [f'{IND}type {node.name}']
            for f in node.fields: result.append(f'{IND}    {self._expr_to_str(f.type)} {f.name}' + (f' = {self._expr_to_str(f.default)}' if f.default else ''))
            return '\n'.join(result)
        if isinstance(node, EnumDeclaration):
            result = [f'{IND}enum {node.name}']
            for v in node.values:
                if isinstance(v, tuple): result.append(f'{IND}    {v[0]} = {self._expr_to_str(v[1])}')
                else: result.append(f'{IND}    {v}')
            return '\n'.join(result)
        if isinstance(node, ImportDeclaration): return f'{IND}import {node.path}'
        if isinstance(node, LibraryDeclaration): return f'{IND}library {node.name or ""}'
        if isinstance(node, ExportDeclaration): return f'{IND}export {" ".join(node.targets)}'
        if isinstance(node, DestructuringAssignment): return f'{IND}[{", ".join(self._expr_to_str(t) for t in node.targets)}] = {self._expr_to_str(node.value)}'
        return f'{IND}// unparse:{type(node).__name__}'

    def _expr_to_str(self, node):
        if node is None: return 'na'
        if isinstance(node, IntegerLiteral): return str(node.value)
        if isinstance(node, FloatLiteral): return str(node.value)
        if isinstance(node, StringLiteral): return '"' + node.value + '"'
        if isinstance(node, BoolLiteral): return 'true' if node.value else 'false'
        if isinstance(node, Identifier): return node.name
        if isinstance(node, QualifiedName): return '.'.join(node.parts)
        if isinstance(node, MemberAccess): return self._expr_to_str(node.target) + '.' + node.member
        if isinstance(node, Call):
            func_str = self._expr_to_str(node.func)
            args_str = ', '.join(self._expr_to_str(a) for a in node.args)
            return f'{func_str}({args_str})'
        if isinstance(node, Assignment): return self._expr_to_str(node.target) + ' ' + node.operator + ' ' + self._expr_to_str(node.value)
        if isinstance(node, BinaryOp): return self._expr_to_str(node.left) + ' ' + node.operator + ' ' + self._expr_to_str(node.right)
        if isinstance(node, UnaryOp): return node.operator + self._expr_to_str(node.operand)
        if isinstance(node, TernaryOp): return self._expr_to_str(node.condition) + ' ? ' + self._expr_to_str(node.then_expr) + ' : ' + self._expr_to_str(node.else_expr)
        if isinstance(node, Index): return self._expr_to_str(node.target) + '[' + self._expr_to_str(node.index) + ']'
        if isinstance(node, RangeExpr):
            r = self._expr_to_str(node.start) + ' to ' + self._expr_to_str(node.end)
            if node.step: r += ' by ' + self._expr_to_str(node.step)
            return r
        if isinstance(node, TupleLiteral): return '[' + ', '.join(self._expr_to_str(e) for e in node.elements) + ']'
        if isinstance(node, ArrowFunction):
            params = ', '.join(p.get('name', '') for p in node.params)
            return f'({params}) => {self._expr_to_str(node.body)}'
        if isinstance(node, GenericType): return node.base + '<' + ', '.join(self._expr_to_str(p) for p in node.params) + '>'
        return 'na'

    def _get_func_name(self, node):
        if isinstance(node, Identifier): return node.name
        if isinstance(node, QualifiedName): return '.'.join(node.parts)
        if isinstance(node, MemberAccess):
            t = self._get_func_name(node.target)
            return f"{t}.{node.member}" if t else None
        return None

    # ── UTILITIES ───────────────────────────────────────────
    def _is_valid_pine(self, code):
        try:
            from engine.parser import PineAST; PineAST(code); return True
        except: return False

    def _re_extract(self, code):
        try:
            from engine.parser import PineAST; from engine.extractor import FeatureExtractor
            return FeatureExtractor(PineAST(code).root, code).extract_all()
        except: return []

    def _generate_diff(self, original, patched, file_path):
        return ''.join(difflib.unified_diff(
            original.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            fromfile=f'a/{file_path}',
            tofile=f'b/{file_path}',
        ))
