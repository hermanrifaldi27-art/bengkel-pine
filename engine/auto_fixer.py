#!/usr/bin/env python3
"""
Auto-Fixer v10.10.1 FINAL MASTER ★★★★★ — Production-Grade Compiler Tool for Pine Script™ v6
Kompatibel dengan PineAST v4.0.2 (tanpa Comment/ColorLiteral/Block).
"""
import difflib
import os
import shutil
import copy
import sys
import json
import time
import hashlib
import pickle
from typing import List, Optional, Dict, Any, Tuple, Set
from dataclasses import dataclass
from types import MappingProxyType

# ============================================================
# DEPENDENSI & FALLBACK
# ============================================================
try:
    from engine.knowledge_base_proactive import ProactiveKnowledgeBase
except ImportError:
    class ProactiveKnowledgeBase:
        def get_confidence(self, f): return 1.0

try:
    from engine.types import (
        PineType, TYPE_BOX, TYPE_LABEL, TYPE_LINE, TYPE_LINEFILL, TYPE_POLYLINE,
        Qualifier, SERIES, CONST, INPUT, SIMPLE
    )
    from engine.pine_builtins import BuiltinRegistry, BuiltinFunction, OverloadResolver
    TYPE_AWARE_AVAILABLE = True
except ImportError:
    TYPE_AWARE_AVAILABLE = False
    PineType = TYPE_BOX = TYPE_LABEL = TYPE_LINE = TYPE_LINEFILL = TYPE_POLYLINE = None
    Qualifier = SERIES = CONST = INPUT = SIMPLE = None
    BuiltinRegistry = BuiltinFunction = OverloadResolver = None

try:
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
    # Fallback untuk kelas yang tidak ada di parser Anda
    try:
        from engine.parser import Comment
    except ImportError:
        Comment = None
    try:
        from engine.parser import ColorLiteral
    except ImportError:
        ColorLiteral = None
    try:
        from engine.parser import Block
    except ImportError:
        Block = None
except ImportError as e:
    print(f"❌ Gagal import parser: {e}")
    sys.exit(1)

# ============================================================
# FUNGSI UTILITAS BERSAMA
# ============================================================
def all_child_nodes(node):
    """Mengembalikan iterator ke semua anak ASTNode."""
    if hasattr(node, 'children'):
        for child in node.children():
            yield child
    else:
        for attr, val in vars(node).items():
            if attr.startswith('_'):
                continue
            if isinstance(val, ASTNode):
                yield val
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, ASTNode):
                        yield item
                    elif isinstance(item, tuple):
                        for t in item:
                            if isinstance(t, ASTNode):
                                yield t
            elif isinstance(val, tuple):
                for t in val:
                    if isinstance(t, ASTNode):
                        yield t

def ensure_str(node, attr='name') -> Optional[str]:
    val = getattr(node, attr, None)
    if val is None:
        return None
    if isinstance(val, str):
        return val.strip() or None
    if isinstance(val, Identifier):
        return val.name
    return None

def get_lineno(node) -> int:
    for a in ('lineno', 'line'):
        if hasattr(node, a):
            val = getattr(node, a, 0)
            return val if isinstance(val, int) else 0
    if hasattr(node, 'pos') and hasattr(node.pos, 'line'):
        return node.pos.line
    return 0

def get_col(node) -> int:
    for a in ('col_offset', 'column', 'col'):
        if hasattr(node, a):
            val = getattr(node, a, 0)
            return val if isinstance(val, int) else 0
    if hasattr(node, 'pos') and hasattr(node.pos, 'column'):
        return node.pos.column
    return 0

# ============================================================
# SATU SUMBER KEBENARAN
# ============================================================
BUILTIN_SYMBOLS = {}
ENUM_MAP = {}

if TYPE_AWARE_AVAILABLE and BuiltinRegistry is not None:
    try:
        if hasattr(BuiltinRegistry, 'get_all_symbols'):
            BUILTIN_SYMBOLS = BuiltinRegistry.get_all_symbols()
            print(f"✅ Dimuat {len(BUILTIN_SYMBOLS)} simbol dari BuiltinRegistry")
        else:
            registry = BuiltinRegistry()
            if hasattr(registry, 'get_all_symbols'):
                BUILTIN_SYMBOLS = registry.get_all_symbols()
            else:
                BUILTIN_SYMBOLS = {}
        if hasattr(BuiltinRegistry, 'get_all_enums'):
            ENUM_MAP = BuiltinRegistry.get_all_enums()
        else:
            ENUM_MAP = {}
    except Exception as e:
        print(f"⚠️ Gagal memuat BuiltinRegistry: {e}")
        BUILTIN_SYMBOLS = {}
        ENUM_MAP = {}
else:
    print("ℹ️ BuiltinRegistry tidak tersedia — auto-fixer berjalan dalam mode dasar.")

# FALLBACK MINIMAL
if not BUILTIN_SYMBOLS:
    BUILTIN_SYMBOLS = {
        'ta': ('namespace', None), 'math': ('namespace', None), 'request': ('namespace', None),
        'strategy': ('namespace', None), 'input': ('namespace', None), 'str': ('namespace', None),
        'barstate': ('namespace', None), 'syminfo': ('namespace', None), 'color': ('namespace', None),
        'time': ('namespace', None), 'chart': ('namespace', None), 'timeframe': ('namespace', None),
        'session': ('namespace', None), 'ticker': ('namespace', None), 'array': ('namespace', None),
        'matrix': ('namespace', None), 'map': ('namespace', None), 'table': ('namespace', None),
        'box': ('namespace', None), 'line': ('namespace', None), 'label': ('namespace', None),
        'polyline': ('namespace', None), 'linefill': ('namespace', None), 'plot': ('namespace', None),
        'display': ('namespace', None), 'size': ('namespace', None), 'barmerge': ('namespace', None),
        'xloc': ('namespace', None), 'yloc': ('namespace', None), 'extend': ('namespace', None),
        'location': ('namespace', None), 'position': ('namespace', None), 'scale': ('namespace', None),
        'shape': ('namespace', None), 'text': ('namespace', None), 'font': ('namespace', None),
        'runtime': ('namespace', None), 'log': ('namespace', None), 'currency': ('namespace', None),
        'strategy.risk': ('namespace', None),
    }
    print("⚠️ Menggunakan fallback namespace minimal (tidak ada enum/signature)")

# ============================================================
# SYMBOL & SCOPE
# ============================================================
@dataclass(frozen=True)
class SymbolInfo:
    name: str
    type_str: Optional[str] = None
    return_type_str: Optional[str] = None
    qualifier: Optional[str] = None
    kind: str = 'var'
    is_global: bool = False
    decl_preorder: int = -1
    decl_line: int = -1
    decl_col: int = -1

@dataclass(frozen=True)
class ScopeSnapshot:
    symbols: MappingProxyType
    parent_id: Optional[int] = None
    scope_id: int = -1

    @classmethod
    def build(cls, symbols: Dict[str, SymbolInfo], parent_id: Optional[int] = None, scope_id: int = -1):
        return cls(symbols=MappingProxyType(dict(symbols)), parent_id=parent_id, scope_id=scope_id)

    def resolve(self, name: str, preorder: int = -1, line: int = -1, col: int = -1) -> Optional[SymbolInfo]:
        info = self.symbols.get(name)
        if info:
            if preorder >= 0 and info.decl_preorder >= 0:
                if info.decl_preorder > preorder:
                    return None
                if info.decl_preorder == preorder:
                    if info.decl_line > line:
                        return None
                    if info.decl_line == line and info.decl_col > col:
                        return None
            return info
        return None

# ============================================================
# SCOPE BUILDER
# ============================================================
class ScopeBuilder:
    def __init__(self):
        self.scope_by_id: Dict[int, ScopeSnapshot] = {}
        self.node_scope_map: Dict[str, int] = {}
        self.next_scope_id = 1
        self.preorder_counter = 0
        self._declarations: Dict[int, List[SymbolInfo]] = {}
        self._scope_id_for_node: Dict[str, int] = {}

    def build(self, root: ASTNode) -> Tuple[Dict[int, ScopeSnapshot], Dict[str, int]]:
        self._assign_preorder(root)
        self._collect_declarations(root)

        stack = [(root, None)]
        while stack:
            node, parent_scope_id = stack.pop()
            uid = getattr(node, '_runtime_uid', '')
            tentative_scope_id = self._scope_id_for_node.get(uid)
            current_scope_id = parent_scope_id

            if tentative_scope_id is not None:
                scope_id = tentative_scope_id
                symbols: Dict[str, SymbolInfo] = {}
                if parent_scope_id is not None and parent_scope_id in self.scope_by_id:
                    parent_snap = self.scope_by_id[parent_scope_id]
                    for name, sym in parent_snap.symbols.items():
                        symbols[name] = sym
                if isinstance(node, Module):
                    for name, (kind, t) in BUILTIN_SYMBOLS.items():
                        if name not in symbols:
                            symbols[name] = SymbolInfo(name=name, type_str=t, kind=kind, is_global=True)
                if isinstance(node, (FunctionDeclaration, MethodDeclaration)):
                    for p in getattr(node, 'params', []):
                        name = ensure_str(p, 'name')
                        ptype = AutoFixerFinal._type_to_str_qualified_static(self._pick_type(p))
                        if name and name not in symbols:
                            symbols[name] = SymbolInfo(name=name, type_str=ptype, kind='param',
                                                       decl_preorder=getattr(p, '_preorder_idx', -1),
                                                       decl_line=get_lineno(p),
                                                       decl_col=get_col(p))
                    if isinstance(node, MethodDeclaration):
                        rec = getattr(node, 'receiver', None)
                        if rec:
                            rname = ensure_str(rec, 'name')
                            rtype = AutoFixerFinal._type_to_str_qualified_static(self._pick_type(rec))
                            if rname and rname not in symbols:
                                symbols[rname] = SymbolInfo(name=rname, type_str=rtype, kind='receiver',
                                                           decl_preorder=getattr(rec, '_preorder_idx', -1))
                for sym in self._declarations.get(scope_id, []):
                    if sym.name not in symbols:
                        symbols[sym.name] = sym
                snap = ScopeSnapshot.build(symbols, parent_scope_id, scope_id)
                self.scope_by_id[scope_id] = snap
                self.node_scope_map[uid] = scope_id
                current_scope_id = scope_id

                if isinstance(node, FunctionDeclaration) and parent_scope_id is not None:
                    parent_snap = self.scope_by_id[parent_scope_id]
                    parent_symbols = dict(parent_snap.symbols)
                    fname = ensure_str(node, 'name')
                    if fname and fname not in parent_symbols:
                        parent_symbols[fname] = SymbolInfo(name=fname, kind='function',
                                                           return_type_str=AutoFixerFinal._type_to_str_qualified_static(getattr(node, 'return_type', None)),
                                                           decl_preorder=getattr(node, '_preorder_idx', -1))
                        self.scope_by_id[parent_scope_id] = ScopeSnapshot.build(parent_symbols, parent_snap.parent_id, parent_scope_id)
                if isinstance(node, MethodDeclaration) and parent_scope_id is not None:
                    parent_snap = self.scope_by_id[parent_scope_id]
                    parent_symbols = dict(parent_snap.symbols)
                    mname = ensure_str(node, 'name')
                    if mname and mname not in parent_symbols:
                        parent_symbols[mname] = SymbolInfo(name=mname, kind='method',
                                                           return_type_str=AutoFixerFinal._type_to_str_qualified_static(getattr(node, 'return_type', None)),
                                                           decl_preorder=getattr(node, '_preorder_idx', -1))
                        self.scope_by_id[parent_scope_id] = ScopeSnapshot.build(parent_symbols, parent_snap.parent_id, parent_scope_id)
            else:
                self.node_scope_map[uid] = current_scope_id

            children = list(all_child_nodes(node))
            for child in reversed(children):
                stack.append((child, current_scope_id))

        return self.scope_by_id, self.node_scope_map

    def _collect_declarations(self, node):
        stack = [(node, None)]
        while stack:
            n, parent_scope_id = stack.pop()
            uid = getattr(n, '_runtime_uid', '')
            if isinstance(n, (Module, FunctionDeclaration, MethodDeclaration)):
                scope_id = self.next_scope_id
                self.next_scope_id += 1
                self._scope_id_for_node[uid] = scope_id
            elif parent_scope_id is not None:
                scope_id = parent_scope_id
            else:
                scope_id = 0

            pre = getattr(n, '_preorder_idx', -1)
            line = get_lineno(n)
            col = get_col(n)
            if isinstance(n, (VarDeclaration, ConstDeclaration)):
                name = ensure_str(n, 'name')
                if name:
                    qual = getattr(n, 'qualifier', None)
                    kind = 'varip' if qual and qual.lower() == 'varip' else 'var'
                    self._declarations.setdefault(scope_id, []).append(
                        SymbolInfo(name=name, type_str=AutoFixerFinal._type_to_str_qualified_static(getattr(n, 'type', None)),
                                   kind=kind, decl_preorder=pre, decl_line=line, decl_col=col)
                    )
            elif isinstance(n, ForInStatement):
                for t in getattr(n, 'targets', []):
                    name = ensure_str(t)
                    if name:
                        self._declarations.setdefault(scope_id, []).append(
                            SymbolInfo(name=name, type_str='any', kind='var', decl_preorder=pre, decl_line=line, decl_col=col)
                        )
            elif isinstance(n, ImportDeclaration):
                path_parts = n.path.split('/')
                ns = path_parts[-1].split('.')[0]
                if hasattr(n, 'alias') and n.alias:
                    ns = n.alias
                if ns:
                    self._declarations.setdefault(scope_id, []).append(
                        SymbolInfo(name=ns, type_str='namespace', kind='import', decl_preorder=pre)
                    )
            elif isinstance(n, LibraryDeclaration):
                if n.name:
                    self._declarations.setdefault(scope_id, []).append(
                        SymbolInfo(name=n.name, type_str='namespace', kind='library', decl_preorder=pre)
                    )
            elif isinstance(n, TypeDeclaration):
                if n.name:
                    self._declarations.setdefault(scope_id, []).append(
                        SymbolInfo(name=n.name, type_str='type', kind='type', decl_preorder=pre)
                    )
            elif isinstance(n, EnumDeclaration):
                if n.name:
                    self._declarations.setdefault(scope_id, []).append(
                        SymbolInfo(name=n.name, type_str='enum', kind='enum', decl_preorder=pre)
                    )

            children = list(all_child_nodes(n))
            for child in reversed(children):
                stack.append((child, scope_id))

    def _assign_preorder(self, root):
        self.preorder_counter = 0
        stack = [root]
        while stack:
            node = stack.pop()
            setattr(node, '_preorder_idx', self.preorder_counter)
            self.preorder_counter += 1
            children = list(all_child_nodes(node))
            for child in reversed(children):
                stack.append(child)

    def _pick_type(self, node):
        return getattr(node, 'type', None) or getattr(node, 'type_str', None)

# ============================================================
# TYPE AWARE FIXER
# ============================================================
class TypeAwareFixer:
    def __init__(self, registry=None):
        if registry is None and TYPE_AWARE_AVAILABLE:
            try:
                self.registry = BuiltinRegistry()
            except Exception:
                self.registry = None
        else:
            self.registry = registry
        self.fix_errors: List[str] = []
        self._type_cache: Dict[str, str] = {}
        self._strict_mode = False
        self._type_stack: Set[str] = set()

    def set_strict_mode(self, strict: bool):
        self._strict_mode = strict

    def clear_cache(self):
        self._type_cache.clear()
        self._type_stack.clear()

    @staticmethod
    def _split_qualifier(t: str) -> Tuple[Optional[str], str]:
        if ' ' in t:
            q, b = t.split(' ', 1)
            return q, b
        return None, t

    @staticmethod
    def _qualifier_strength(q: Optional[str]) -> int:
        STRENGTH = {'const': 4, 'input': 3, 'simple': 2, 'series': 1, None: 0}
        return STRENGTH.get(q, 0)

    def _check_min_params(self, call_node, func_def) -> bool:
        if func_def is None:
            return True
        min_params = getattr(func_def, 'min_params', None)
        if min_params is None:
            if hasattr(func_def, 'overloads') and func_def.overloads:
                best = max(func_def.overloads, key=lambda o: len([p for p in o.params if not getattr(p, 'optional', False)]))
                min_params = len([p for p in best.params if not getattr(p, 'optional', False)])
            else:
                min_params = 0
        pos_args = [a for a in call_node.args if not isinstance(a, Assignment)]
        named_args = [a for a in call_node.args if isinstance(a, Assignment)]
        total_valid = len(pos_args) + len(named_args)
        if total_valid < min_params:
            self.fix_errors.append(f"⚠️ Fungsi {getattr(func_def, 'name', '?')} memerlukan minimal {min_params} parameter, hanya {total_valid} diberikan")
            return False
        return True

    def _check_duplicate_named_args(self, call_node, func_def=None) -> bool:
        names = {}
        for idx, arg in enumerate(call_node.args):
            if isinstance(arg, Assignment) and isinstance(arg.target, Identifier):
                nm = arg.target.name
                if nm in names:
                    self.fix_errors.append(f"⚠️ Argumen '{nm}' diduplikasi posisi {names[nm]} dan {idx}")
                    return False
                names[nm] = idx
        if func_def and hasattr(func_def, 'overloads'):
            best = max(func_def.overloads, key=lambda o: len(o.params))
            pos_count = 0
            for arg in call_node.args:
                if isinstance(arg, Assignment):
                    break
                pos_count += 1
            param_names = [p.name for p in best.params]
            for i in range(pos_count):
                if i < len(param_names) and param_names[i] in names:
                    self.fix_errors.append(f"⚠️ Parameter posisi {i} tumpang tindih dengan argumen bernama")
                    return False
        return True

    def fix_call(self, call_node, scope_snap: Optional[ScopeSnapshot], preorder: int, line: int, col: int):
        modified = False
        self.fix_errors = []
        if not TYPE_AWARE_AVAILABLE or self.registry is None:
            return call_node, modified

        func_name = self._get_full_name(call_node.func)
        if not func_name:
            return call_node, modified

        func_def = self.registry.resolve(func_name.split('.'))
        if not func_def or not isinstance(func_def, BuiltinFunction):
            return call_node, modified

        if not self._check_duplicate_named_args(call_node, func_def):
            return call_node, False

        candidate = copy.deepcopy(call_node)

        if not self._check_min_params(candidate, func_def):
            return call_node, False

        scope_id = scope_snap.scope_id if scope_snap else None
        arg_types = [self._infer_type(arg, scope_snap, preorder, line, col, scope_id) for arg in candidate.args]
        matched = self._resolve_best_overload(func_def, arg_types)
        if not matched:
            if self._fix_enum_values(candidate, func_def):
                modified = True
                arg_types = [self._infer_type(arg, scope_snap, preorder, line, col, scope_id) for arg in candidate.args]
                matched = self._resolve_best_overload(func_def, arg_types)
            if not matched:
                return call_node, modified

        existing_names = {a.target.name for a in candidate.args if isinstance(a, Assignment) and isinstance(a.target, Identifier)}
        for param in matched.params:
            if getattr(param, 'optional', False) and getattr(param, 'default', None) is not None:
                if param.name not in existing_names:
                    candidate.args.append(Assignment(
                        target=Identifier(name=param.name),
                        value=AutoFixerFinal._default_to_ast_safe(param.default),
                        operator='='
                    ))
                    modified = True
                    self.fix_errors.append(f"✅ Tambah opsional: {param.name}")

        if modified:
            expr_str = AutoFixerFinal._expr_to_str_static(candidate)
            temp_code = f" _ = {expr_str}"
            if not AutoFixerFinal._is_valid_pine_syntax(temp_code):
                self.fix_errors.append("⚠️ Dibatalkan: hasil tidak valid")
                return call_node, False
            call_node.args = candidate.args
        return call_node, modified

    def fix_var_declaration(self, var_node, scope_snap, preorder, line, col):
        if var_node.type is not None:
            return var_node, False
        if isinstance(var_node.value, Call):
            func_name = self._get_full_name(var_node.value.func)
            if func_name and self.registry:
                func_def = self.registry.resolve(func_name.split('.'))
                if func_def and hasattr(func_def, 'return_type'):
                    full_type = AutoFixerFinal._type_to_str_qualified_static(func_def.return_type)
                    if full_type:
                        var_node.type = full_type
                        return var_node, True
        return var_node, False

    def _fix_boolean_strict(self, node) -> bool:
        modified = False
        if isinstance(node, VarDeclaration) and getattr(node, 'type', None) == 'bool':
            if isinstance(node.value, Identifier) and node.value.name == 'na':
                node.value = BoolLiteral(value=False)
                self.fix_errors.append("✅ bool = na → bool = false (v6 strict)")
                modified = True
        if isinstance(node, TernaryOp):
            if (isinstance(node.then_expr, BoolLiteral) and node.then_expr.value is True and
                isinstance(node.else_expr, Identifier) and node.else_expr.name == 'na'):
                self.fix_errors.append("ℹ️ Ternary 'true:na' bisa disederhanakan menjadi kondisi (v6)")
        return modified

    def _resolve_best_overload(self, func_def, arg_types):
        overloads = self._safe_resolve_overloads(func_def, arg_types)
        if not overloads:
            return None
        scored = [(self._score_overload(o, arg_types), o) for o in overloads]
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score = scored[0][0]
        best = [o for s, o in scored if s == best_score]
        if len(best) > 1:
            best.sort(key=lambda o: len([p for p in o.params if not getattr(p, 'optional', False)]), reverse=True)
            if len(best) > 1:
                param_names = []
                for p in best[0].params[:3]:
                    param_names.append(p.name if hasattr(p, 'name') else '?')
                self.fix_errors.append(
                    f"⚠️ Overload ambigu — parameter {', '.join(param_names)} tidak spesifik, tentukan secara eksplisit"
                )
                return None
        return best[0]

    def _score_overload(self, overload, arg_types):
        score = 0
        params = getattr(overload, 'params', [])
        qual_priority = {'const':4, 'input':3, 'simple':2, 'series':1, None:0}
        for i, p in enumerate(params):
            if getattr(p, 'optional', False):
                score += 1
            if i >= len(arg_types):
                continue
            atype = arg_types[i] if i < len(arg_types) else 'any'
            ptype = AutoFixerFinal._type_to_str_qualified_static(getattr(p, 'type', None)) or 'any'
            pqual = None
            if ' ' in ptype:
                q_candidate = ptype.split(' ')[0]
                if q_candidate in qual_priority:
                    pqual = q_candidate
            if ptype == 'any' or atype == 'any':
                pass
            elif ptype == atype:
                score += 10
            elif self._can_convert(atype, ptype):
                score += 3
            else:
                score -= 5
            if pqual is not None:
                aq = None
                if atype.startswith('const '):
                    aq = 'const'
                elif atype.startswith('input '):
                    aq = 'input'
                elif atype.startswith('series '):
                    aq = 'series'
                elif atype.startswith('simple '):
                    aq = 'simple'
                if aq == pqual:
                    score += 3
                elif qual_priority.get(aq, 0) >= qual_priority.get(pqual, 0):
                    score += 1
        score += sum(1 for i in range(min(len(params), len(arg_types)))
                     if not getattr(params[i], 'optional', False)) * 3
        return score

    def _can_convert(self, from_type, to_type):
        from_qual, base_from = self._split_qualifier(from_type)
        to_qual, base_to = self._split_qualifier(to_type)

        if base_from == base_to:
            type_ok = True
        elif base_from == 'int' and base_to == 'float':
            type_ok = True
        elif base_from == 'any' or base_to == 'any':
            type_ok = True
        else:
            return False

        from_strength = self._qualifier_strength(from_qual)
        to_strength = self._qualifier_strength(to_qual)
        return type_ok and from_strength >= to_strength

    def _safe_resolve_overloads(self, func_def, arg_types):
        if hasattr(OverloadResolver, 'resolve_all'):
            return OverloadResolver.resolve_all(func_def.overloads, arg_types) or []
        if hasattr(OverloadResolver, 'resolve'):
            matched = OverloadResolver.resolve(func_def.overloads, arg_types)
            return [matched] if matched else []
        return []

    def _infer_type(self, node, scope_snap, preorder, line, col, scope_id):
        key = f"{getattr(node, '_runtime_uid', '')}@{scope_id}" if scope_id is not None else getattr(node, '_runtime_uid', '')
        if key in self._type_cache:
            return self._type_cache[key]

        node_uid = getattr(node, '_runtime_uid', str(id(node)))
        stack_key = f"{node_uid}@{scope_id}"
        if stack_key in self._type_stack:
            self.fix_errors.append(f"⚠️ Siklus referensi tipe terdeteksi pada {node_uid} di scope {scope_id}")
            return 'any'

        self._type_stack.add(stack_key)
        try:
            result = self._infer_type_unsafe(node, scope_snap, preorder, line, col, scope_id)
        finally:
            self._type_stack.discard(stack_key)
        self._type_cache[key] = result
        return result

    def _infer_type_unsafe(self, node, scope_snap, preorder, line, col, scope_id):
        if isinstance(node, IntegerLiteral):
            return 'int'
        if isinstance(node, FloatLiteral):
            return 'float'
        if isinstance(node, StringLiteral):
            return 'string'
        if isinstance(node, BoolLiteral):
            return 'bool'
        if isinstance(node, Identifier):
            if scope_snap:
                info = scope_snap.resolve(node.name, preorder, line, col)
                if info:
                    return info.return_type_str or info.type_str or 'any'
            if node.name in BUILTIN_SYMBOLS:
                _, t = BUILTIN_SYMBOLS[node.name]
                return t if t else 'any'
            return 'any'
        if isinstance(node, MemberAccess):
            target_type = self._infer_type(node.target, scope_snap, preorder, line, col, scope_id)
            _, base = self._split_qualifier(target_type)
            member = node.member
            full_name = f"{base}.{member}" if base != 'any' else member
            if self.registry:
                fdef = self.registry.resolve(full_name.split('.'))
                if fdef:
                    if hasattr(fdef, 'return_type'):
                        return AutoFixerFinal._type_to_str_qualified_static(fdef.return_type) or 'any'
                    elif hasattr(fdef, 'type'):
                        return AutoFixerFinal._type_to_str_qualified_static(fdef.type) or 'any'
            return 'any'
        if isinstance(node, QualifiedName):
            full_name = '.'.join(node.parts)
            if self.registry:
                fdef = self.registry.resolve(full_name.split('.'))
                if fdef and hasattr(fdef, 'return_type'):
                    return AutoFixerFinal._type_to_str_qualified_static(fdef.return_type) or 'any'
            if full_name in BUILTIN_SYMBOLS:
                _, t = BUILTIN_SYMBOLS[full_name]
                return t if t else 'any'
            return 'any'
        if isinstance(node, Call) and self.registry:
            fname = self._get_full_name(node.func)
            if fname == 'request.security' and len(node.args) >= 3:
                expr_type = self._infer_type(node.args[2], scope_snap, preorder, line, col, scope_id)
                if not expr_type.startswith('series '):
                    expr_type = 'series ' + expr_type
                return expr_type
            if fname and self.registry:
                fdef = self.registry.resolve(fname.split('.'))
                if fdef and hasattr(fdef, 'return_type'):
                    return AutoFixerFinal._type_to_str_qualified_static(fdef.return_type) or 'any'
            return 'any'
        if isinstance(node, TupleLiteral):
            elem_types = [self._infer_type(e, scope_snap, preorder, line, col, scope_id) for e in node.elements]
            return f"tuple({','.join(elem_types)})" if elem_types else 'tuple'
        if isinstance(node, GenericType):
            return AutoFixerFinal._type_to_str_qualified_static(node) or 'generic'
        return 'any'

    def _fix_enum_values(self, call_node, func_def):
        enum_map = getattr(func_def, 'enum_map', None) or ENUM_MAP
        if not enum_map:
            return False

        modified = False
        best_overload = max(func_def.overloads, key=lambda o: len(o.params))
        param_names = [p.name for p in best_overload.params if hasattr(p, 'name')]

        for idx, arg in enumerate(call_node.args):
            param_name = param_names[idx] if idx < len(param_names) else None
            if isinstance(arg, Assignment) and isinstance(arg.target, Identifier):
                pname = arg.target.name
                if pname in enum_map and isinstance(arg.value, StringLiteral):
                    val = arg.value.value.lower().strip()
                    mapping = enum_map[pname]
                    if isinstance(mapping, dict) and val in mapping:
                        full_ref = mapping[val]
                        a, b = full_ref.split('.', 1)
                        arg.value = MemberAccess(target=Identifier(name=a), member=b)
                        modified = True
                        self.fix_errors.append(f"✅ Enum: '{val}' → {full_ref}")
                    else:
                        valid = ', '.join(mapping.keys()) if isinstance(mapping, dict) else str(mapping)
                        self.fix_errors.append(f"⚠️ Enum '{pname}' tidak mengenal '{val}'; nilai valid: {valid}")
                        return False
            elif isinstance(arg, StringLiteral) and param_name and param_name in enum_map:
                val = arg.value.lower().strip()
                mapping = enum_map[param_name]
                if isinstance(mapping, dict) and val in mapping:
                    full_ref = mapping[val]
                    a, b = full_ref.split('.', 1)
                    call_node.args[idx] = MemberAccess(target=Identifier(name=a), member=b)
                    modified = True
                    self.fix_errors.append(f"✅ Enum: '{val}' → {full_ref}")
                else:
                    valid = ', '.join(mapping.keys()) if isinstance(mapping, dict) else str(mapping)
                    self.fix_errors.append(f"⚠️ Enum '{param_name}' tidak mengenal '{val}'; nilai valid: {valid}")
                    return False
        return modified

    def _get_full_name(self, node):
        if isinstance(node, Identifier):
            return node.name
        if isinstance(node, QualifiedName):
            return '.'.join(node.parts)
        if isinstance(node, MemberAccess):
            t = self._get_full_name(node.target)
            return f"{t}.{node.member}" if t else None
        return None

# ============================================================
# AUTO-FIXER FINAL MASTER (v10.10.1 + perbaikan)
# ============================================================
class AutoFixerFinal:
    PRECEDENCE = {'unary':8,'**':7,'*':6,'/':6,'%':6,'+':5,'-':5,'<':4,'<=':4,'>':4,'>=':4,
                  '==':3,'!=':3,'and':2,'or':1,'ternary':0,'assignment':-1}

    FORBIDDEN_IN_BLOCK = {
        'plot', 'plotshape', 'plotchar', 'plotarrow', 'plotcandle', 'plotbar',
        'fill', 'bgcolor', 'barcolor', 'hline',
        'alertcondition', 'indicator', 'strategy', 'library', 'export'
    }

    MAX_REQUEST_SECURITY = 40

    def __init__(self, kb=None, registry=None, strict=False):
        self.kb = kb or ProactiveKnowledgeBase()
        self.min_confidence = 0.7
        self.rollback_states: Dict[str, Tuple[str, str, str]] = {}
        self._load_rollback_states()
        self.fix_errors: List[str] = []
        self.type_fixer = TypeAwareFixer(registry) if TYPE_AWARE_AVAILABLE else None
        if self.type_fixer:
            self.type_fixer.set_strict_mode(strict)
        self._original_newline = '\n'
        self._runtime_uid_counter = 0
        self._patch_report: List[Dict] = []
        self._json_output_path = None
        self._ast_cache: Dict[str, Any] = {}
        self._ast_hash_cache: Dict[str, str] = {}
        self._strict_mode = strict
        self._report_only = False
        self._unsupported_nodes: Set[str] = set()
        self._request_security_count = 0
        self._modified_positions: Set[int] = set()
        self._pine_version = 6
        self._max_passes = 2
        self._max_changes_per_file = 0.05
        self._min_changes_allowed = 3
        self._injected_names: Set[str] = set()
        self._injected_var_map: Dict[str, str] = {}

    def _load_rollback_states(self):
        try:
            with open('.auto_fixer_rollback.pkl', 'rb') as f:
                self.rollback_states = pickle.load(f)
                print(f"✅ Dimuat {len(self.rollback_states)} status rollback dari disk")
        except Exception:
            pass

    def _save_rollback_states(self):
        try:
            with open('.auto_fixer_rollback.pkl', 'wb') as f:
                pickle.dump(self.rollback_states, f)
        except Exception as e:
            print(f"⚠️ Gagal menyimpan status rollback: {e}")

    def _get_pine_version(self, code: str) -> int:
        for line in code.split('\n'):
            if line.strip().startswith('//@version='):
                try:
                    return int(line.strip().split('=')[1].strip())
                except:
                    pass
        return 6

    def _is_in_block(self, node) -> bool:
        current = getattr(node, 'parent', None)
        while current is not None:
            if isinstance(current, (IfStatement, ForStatement, WhileStatement, ForInStatement, SwitchStatement)):
                return True
            current = getattr(current, 'parent', None)
        return False

    def _condition_contains_barstate_last(self, cond) -> bool:
        if cond is None:
            return False
        if isinstance(cond, MemberAccess):
            target_name = getattr(cond.target, 'name', None) if hasattr(cond.target, 'name') else None
            if target_name == 'barstate' and cond.member in ('islast', 'islastconfirmedhistory', 'isconfirmed', 'isnew'):
                return True
        if isinstance(cond, Call):
            fn = self._get_func_name(cond.func)
            if fn in ('barstate.islast', 'barstate.islastconfirmedhistory', 'barstate.isconfirmed'):
                return True
        if isinstance(cond, BinaryOp):
            return (self._condition_contains_barstate_last(cond.left) or
                    self._condition_contains_barstate_last(cond.right))
        if isinstance(cond, UnaryOp):
            return self._condition_contains_barstate_last(cond.operand)
        if isinstance(cond, TernaryOp):
            return (self._condition_contains_barstate_last(cond.condition) or
                    self._condition_contains_barstate_last(cond.then_expr) or
                    self._condition_contains_barstate_last(cond.else_expr))
        if isinstance(cond, Identifier):
            pass
        return False

    def _is_in_barstate_last(self, node) -> bool:
        current = getattr(node, 'parent', None)
        while current is not None:
            if isinstance(current, IfStatement):
                if self._condition_contains_barstate_last(getattr(current, 'condition', None)):
                    return True
            if isinstance(current, SwitchStatement):
                val = getattr(current, 'value', None)
                if self._condition_contains_barstate_last(val):
                    return True
                for case_val, _ in getattr(current, 'cases', []):
                    if self._condition_contains_barstate_last(case_val):
                        return True
            current = getattr(current, 'parent', None)
        return False

    def _is_forbidden_in_block(self, func_name: str) -> bool:
        if func_name in self.FORBIDDEN_IN_BLOCK:
            return True
        if func_name.startswith('input.'):
            return True
        if func_name.startswith('request.'):
            return False
        return False

    def _needs_bool_cast(self, node) -> bool:
        if isinstance(node, (IntegerLiteral, FloatLiteral)):
            return True
        if isinstance(node, BinaryOp) and node.operator in ('+', '-', '*', '/', '%'):
            return True
        return False

    def _find_outermost_function_or_module(self, node):
        current = getattr(node, 'parent', None)
        while current is not None:
            if isinstance(current, (Module, FunctionDeclaration, MethodDeclaration)):
                return current
            current = getattr(current, 'parent', None)
        return None

    def _replace_node(self, parent, old_node, new_node) -> bool:
        if parent is None:
            return False
        if isinstance(parent, tuple):
            self.fix_errors.append("⚠️ _replace_node: parent adalah tuple, tidak dapat mengganti node.")
            return False
        if isinstance(parent, ExpressionStatement) and parent.expression is old_node:
            parent.expression = new_node
            if hasattr(new_node, 'parent'):
                new_node.parent = parent
            return True
        for attr, val in list(vars(parent).items()):
            if attr.startswith('_'):
                continue
            if isinstance(val, list):
                for i, item in enumerate(val):
                    if item is old_node:
                        val[i] = new_node
                        if hasattr(new_node, 'parent'):
                            new_node.parent = parent
                        return True
                    if isinstance(item, tuple):
                        new_tuple = list(item)
                        changed = False
                        for j, t in enumerate(new_tuple):
                            if t is old_node:
                                new_tuple[j] = new_node
                                changed = True
                        if changed:
                            val[i] = tuple(new_tuple)
                            if hasattr(new_node, 'parent'):
                                new_node.parent = parent
                            return True
            elif val is old_node:
                setattr(parent, attr, new_node)
                if hasattr(new_node, 'parent'):
                    new_node.parent = parent
                return True
        return False

    def _has_assignment_to(self, node, var_name: str) -> bool:
        if node is None:
            return False
        stack = [node]
        while stack:
            current = stack.pop()
            if isinstance(current, Assignment):
                target = getattr(current, 'target', None)
                if isinstance(target, Identifier) and target.name == var_name:
                    return True
                if isinstance(target, TupleLiteral):
                    for elem in target.elements:
                        if isinstance(elem, Identifier) and elem.name == var_name:
                            return True
            for child in all_child_nodes(current):
                stack.append(child)
        return False

    def _cleanup_caches(self):
        self._ast_cache.clear()
        self._ast_hash_cache.clear()
        if self.type_fixer:
            self.type_fixer.clear_cache()
        self._modified_positions.clear()
        self._injected_names.clear()
        self._injected_var_map.clear()

    # ============================================================
    # ENTRY POINT
    # ============================================================
    def fix(self, file_path, code, features=None, dry_run=True, auto_confirm=False,
            json_output: Optional[str] = None, report_only: bool = False):
        if features is None:
            return None, 0

        self._report_only = report_only
        self._pine_version = self._get_pine_version(code)
        print(f"ℹ️ Mendeteksi Pine Script v{self._pine_version}")
        if self._report_only:
            print("ℹ️ Mode REPORT-ONLY: hanya menganalisis, tidak mengubah kode")

        self._json_output_path = json_output
        self._patch_report = []
        self._unsupported_nodes.clear()
        self._request_security_count = 0
        self._modified_positions.clear()
        self._injected_names.clear()
        self._injected_var_map.clear()

        if '\r\n' in code:
            self._original_newline = '\r\n'
        elif '\r' in code:
            self._original_newline = '\r'
        else:
            self._original_newline = '\n'
        norm_code = code.replace('\r\n', '\n').replace('\r', '\n')

        self.rollback_states[file_path] = (norm_code, hashlib.sha256(norm_code.encode()).hexdigest(), self._original_newline)
        self.fix_errors.clear()
        if self.type_fixer:
            self.type_fixer.clear_cache()
        self._ast_cache.clear()
        self._ast_hash_cache.clear()
        patched = norm_code
        fixes_applied = 0

        if self._report_only:
            self._generate_report(norm_code, features)
            return None, 0

        for _pass in range(self._max_passes):
            pass_fixes = 0
            features = self._re_extract(patched)
            snapshot_code = patched
            for f in features:
                if self.kb.get_confidence(f) < self.min_confidence:
                    continue
                new_code = self._ast_fix_round_trip(patched, f)
                if new_code is None:
                    if self._strict_mode and self._unsupported_nodes:
                        self.fix_errors.append(f"⚠️ Node tidak dikenal: {', '.join(self._unsupported_nodes)} — perbaikan dibatalkan")
                        continue
                if new_code and new_code != patched and self._is_valid_pine(new_code):
                    if self._ast_structure_valid(new_code, patched):
                        patched = new_code
                        fixes_applied += 1
                        pass_fixes += 1
                        continue
                    else:
                        self.fix_errors.append("⚠️ Struktur berubah — dibatalkan")
                if len(self.fix_errors) > 3:
                    self.fix_errors.append("⚠️ Terlalu banyak peringatan — rollback ke snapshot")
                    patched = snapshot_code
                    break
                if pass_fixes == 0:
                    patched = snapshot_code
                    break
            if pass_fixes == 0:
                break
            self._cleanup_caches()

        if patched == norm_code:
            return None, 0

        print(self._generate_diff(norm_code, patched, file_path))
        if self.fix_errors:
            print(f"\n  ⚠️  {len(self.fix_errors)} perbaikan dibatalkan")
        if dry_run:
            print(f"\n  ✅ {fixes_applied} perbaikan siap diterapkan")
            if self._json_output_path:
                self._write_json_report(file_path, fixes_applied, dry_run=True)
            self._save_rollback_states()
            return patched, fixes_applied
        if not auto_confirm and input(f"Terapkan {fixes_applied} perbaikan? [y/N]: ").strip().lower() != 'y':
            return None, 0

        timestamp = int(time.time())
        backup_path = f"{file_path}.{timestamp}.bak"
        shutil.copy2(file_path, backup_path)
        print(f"📁 Backup: {backup_path}")
        out_code = patched.replace('\n', self._original_newline)
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            f.write(out_code)
        print(f"\n  ✅ {fixes_applied} perbaikan diterapkan (backup: {backup_path})")
        if self._json_output_path:
            self._write_json_report(file_path, fixes_applied, dry_run=False)
        self._save_rollback_states()
        return patched, fixes_applied

    def _generate_report(self, code, features):
        print("\n📋 LAPORAN ANALISIS (REPORT-ONLY):")
        print("=" * 50)
        if not features:
            print("ℹ️ Tidak ada fitur yang perlu diperbaiki.")
            return
        for f in features:
            detector_id = getattr(f, 'detector_id', 'unknown')
            conf = self.kb.get_confidence(f)
            desc = getattr(f, 'description', 'Tidak ada deskripsi')
            actions = []
            if detector_id == 'request_security':
                actions.append("menambahkan gaps/lookahead (jika belum ada)")
            elif detector_id == 'graphics_object_in_block':
                actions.append("menginjeksi var dan assignment")
            elif detector_id == 'forbidden_in_block':
                actions.append("memindahkan fungsi ke luar blok")
            else:
                actions.append("perbaikan otomatis")
            print(f"  • {detector_id} (conf:{conf:.2f}) — {desc} → {', '.join(actions)}")
        print("=" * 50)
        print("ℹ️ Jalankan tanpa --report-only untuk menerapkan perbaikan.")

    def _write_json_report(self, file_path, count, dry_run):
        report = {
            "file": file_path,
            "dry_run": dry_run,
            "report_only": self._report_only,
            "fixes_applied": count,
            "errors": self.fix_errors,
            "changes": self._patch_report,
            "unsupported_nodes": list(self._unsupported_nodes) if self._strict_mode else [],
            "pine_version": self._pine_version,
            "timestamp": time.time()
        }
        try:
            with open(self._json_output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            print(f"⚠️ Gagal menulis JSON: {e}")

    # ============================================================
    # ROLLBACK (PERSISTEN)
    # ============================================================
    def rollback(self, file_path, force=False):
        if file_path not in self.rollback_states:
            print(f"⚠️ Tidak ada rekam rollback untuk {file_path}")
            return False
        orig_code, orig_hash, orig_nl = self.rollback_states[file_path]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                current_code = f.read()
        except Exception as e:
            print(f"❌ Tidak dapat membaca file: {e}")
            return False
        current_sha = hashlib.sha256(current_code.encode()).hexdigest()
        expected_sha = hashlib.sha256(orig_code.encode()).hexdigest()
        if not force and current_sha != orig_hash and current_sha != expected_sha:
            print(f"⚠️ File telah diubah eksternal — gunakan --force untuk memaksa rollback")
            return False
        try:
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                f.write(orig_code)
            print(f"✅ Rollback selesai" + (" (forced)" if force else ""))
            del self.rollback_states[file_path]
            self._save_rollback_states()
            return True
        except Exception as e:
            print(f"❌ Gagal menulis file: {e}")
            return False

    # ============================================================
    # INTI
    # ============================================================
    def _ast_fix_round_trip(self, code, finding):
        cache_key = hashlib.sha256(code.encode()).hexdigest()
        if cache_key in self._ast_cache:
            root = self._ast_cache[cache_key]
            root = copy.deepcopy(root)
        else:
            ast = self._parse_ast(code)
            if ast is None:
                return None
            root = ast.root
            self._ast_cache[cache_key] = root
            root = copy.deepcopy(root)

        self._runtime_uid_counter = 0
        self._assign_runtime_uid(root)

        builder = ScopeBuilder()
        scope_map, node_scope = builder.build(root)

        modified = self._modify_ast_iterative(root, finding, scope_map, node_scope)
        if not modified:
            return None

        new_code = self._unparse_static(root)
        if new_code is None:
            return None
        if not new_code or new_code == code:
            return None
        if not self._ast_structure_valid(new_code, code):
            return None
        return new_code

    def _parse_ast(self, code):
        try:
            from engine.parser import PineAST
            ast = PineAST(code)
            if hasattr(ast, 'errors') and ast.errors:
                return None
            return ast
        except Exception:
            return None

    def _assign_runtime_uid(self, node, parent=None):
        stack = [(node, parent)]
        while stack:
            n, p = stack.pop()
            self._runtime_uid_counter += 1
            setattr(n, '_runtime_uid', f"uid_{self._runtime_uid_counter}")
            setattr(n, 'parent', p)
            children = list(all_child_nodes(n))
            for child in reversed(children):
                stack.append((child, n))

    def _stable_serialize(self, node) -> str:
        typ = type(node).__name__
        parts = [typ]
        if isinstance(node, Identifier):
            parts.append(node.name)
        elif isinstance(node, (IntegerLiteral, FloatLiteral, StringLiteral, BoolLiteral)):
            parts.append(str(getattr(node, 'value', '')))
        elif isinstance(node, (BinaryOp, UnaryOp)):
            parts.append(node.operator)
        elif isinstance(node, MemberAccess):
            parts.append(node.member)
        elif isinstance(node, Assignment):
            parts.append(node.operator)
        elif isinstance(node, FunctionDeclaration):
            parts.append(node.name)
        child_parts = []
        for child in all_child_nodes(node):
            child_parts.append(self._stable_serialize(child))
        parts.append('[' + ','.join(child_parts) + ']')
        return ''.join(parts)

    def _fingerprint(self, node, parent_path: str = "", sibling_idx: int = 0) -> str:
        typ = type(node).__name__
        name = ""
        if isinstance(node, Identifier):
            name = node.name
        elif isinstance(node, (BinaryOp, UnaryOp)):
            name = node.operator
        elif isinstance(node, MemberAccess):
            name = node.member
        elif isinstance(node, Assignment):
            name = node.operator
        elif isinstance(node, FunctionDeclaration):
            name = node.name
        arity = len(list(all_child_nodes(node)))
        stable = self._stable_serialize(node)
        sub_hash = hashlib.sha256(stable.encode()).hexdigest()[:8]
        return f"{parent_path}|{sibling_idx}|{typ}|{name}|{arity}|{sub_hash}"

    # ---------- MODIFIKASI ----------
    def _modify_ast_iterative(self, root, finding, scope_map, node_scope):
        modified = False
        stack = [(root, None, None, False)]
        while stack:
            node, parent, control_parent, visited = stack.pop()
            if visited:
                if self._process_node(node, finding, scope_map, node_scope, parent, control_parent):
                    modified = True
            else:
                new_control = control_parent
                if isinstance(node, (IfStatement, ForStatement, WhileStatement, ForInStatement, SwitchStatement)):
                    new_control = node
                stack.append((node, parent, control_parent, True))
                children = list(all_child_nodes(node))
                for child in reversed(children):
                    stack.append((child, node, new_control, False))
        return modified

    def _process_node(self, node, finding, scope_map, node_scope, parent, control_parent):
        uid = getattr(node, '_runtime_uid', '')
        scope_id = node_scope.get(uid)
        scope_snap = scope_map.get(scope_id) if scope_id is not None else None
        pre = getattr(node, '_preorder_idx', -1)
        line = get_lineno(node)
        col = get_col(node)
        detector_id = getattr(finding, 'detector_id', '')
        modified = False

        if isinstance(node, IfStatement):
            cond = getattr(node, 'condition', None)
            if cond is not None and self._needs_bool_cast(cond):
                self.fix_errors.append(
                    f"ℹ️ Kondisi numerik di baris {line} sebaiknya dibungkus bool() (Pine v6)"
                )

        if isinstance(node, VarDeclaration):
            if getattr(node, 'varip', False) and self._is_in_block(node) and not self._is_in_barstate_last(node):
                self.fix_errors.append(
                    f"ℹ️ varip di dalam blok (baris {line}) — pastikan barstate.islast untuk menghindari perilaku tak terduga"
                )

        if isinstance(node, Call):
            fn = self._get_func_name(node.func)
            if fn and self._is_in_block(node):
                if self._is_forbidden_in_block(fn):
                    self.fix_errors.append(f"⚠️ {fn}() tidak boleh di dalam blok (baris {line}) — perbaikan dibatalkan")
                    return modified

        if isinstance(node, Call) and self.type_fixer:
            fn = self._get_func_name(node.func)
            if fn == 'request.security':
                pass
            if self.type_fixer._fix_boolean_strict(node):
                modified = True
            fixed_call, call_mod = self.type_fixer.fix_call(node, scope_snap, pre, line, col)
            if call_mod:
                modified = True
                self.fix_errors.extend(self.type_fixer.fix_errors)

        if isinstance(node, Call):
            fn = self._get_func_name(node.func)
            if fn == 'request.security' and 'request_security' in detector_id:
                if not self._is_arg_of_call(node, parent):
                    if self._fix_request_security(node, finding, scope_map):
                        modified = True

            if fn in ('box.new', 'label.new', 'line.new', 'linefill.new', 'polyline.new'):
                if self._is_in_block(node) and control_parent is not None:
                    if self._is_in_barstate_last(node):
                        self.fix_errors.append("ℹ️ Di dalam barstate.islast — tidak perlu var, lewati")
                        return modified
                    kind = fn.split('.')[0]
                    var_name = self._inject_object_var(scope_id, scope_map, node_scope, kind, control_parent)
                    if var_name is not None:
                        assign = Assignment(
                            target=Identifier(name=var_name),
                            value=node,
                            operator=':='
                        )
                        if self._replace_node(parent, node, assign):
                            modified = True
                            self._patch_report.append({
                                "type": "graphics_assignment",
                                "kind": kind,
                                "var": var_name,
                                "line": line
                            })
                            self._injected_var_map[f"{kind}_{control_parent}"] = var_name

        if isinstance(node, VarDeclaration) and self.type_fixer:
            fixed_var, var_mod = self.type_fixer.fix_var_declaration(node, scope_snap, pre, line, col)
            if var_mod:
                modified = True
        return modified

    # ---------- INJECT OBJECT VAR ----------
    def _inject_object_var(self, scope_id, scope_map, node_scope, kind, control_parent) -> Optional[str]:
        tmap = {'box':'box','label':'label','line':'line','linefill':'linefill','polyline':'polyline'}
        ptype = tmap.get(kind, 'object')
        if scope_id is None:
            return None

        outer = self._find_outermost_function_or_module(control_parent)
        if outer is None:
            outer = control_parent

        bodies = self._get_all_block_bodies(outer)
        if not bodies:
            if hasattr(control_parent, 'body'):
                bodies = [getattr(control_parent, 'body')]
            else:
                return None

        target_body = bodies[0]

        used_names = set(self._injected_names)
        current_id = scope_id
        while current_id is not None and current_id in scope_map:
            snap = scope_map[current_id]
            used_names.update(snap.symbols.keys())
            current_id = snap.parent_id

        for stmt in target_body:
            if hasattr(stmt, 'name') and stmt.name:
                used_names.add(stmt.name)

        existing_var_name = None
        for stmt in target_body:
            if isinstance(stmt, VarDeclaration) and getattr(stmt, 'type', None) == ptype:
                existing_var_name = getattr(stmt, 'name', None)
                break

        if existing_var_name:
            if self._has_assignment_to(control_parent, existing_var_name):
                existing_var_name = None
            else:
                return existing_var_name

        kind_prefix = {'box':'box', 'label':'label', 'line':'line', 'linefill':'lfill', 'polyline':'poly'}
        prefix = f"_af_{kind_prefix.get(kind, 'obj')}_"
        suffix = len(self._injected_names) + 1
        name = f"{prefix}{suffix}"
        while name in used_names:
            suffix += 1
            name = f"{prefix}{suffix}"
        used_names.add(name)
        self._injected_names.add(name)

        insert_pos = 0
        for i, stmt in enumerate(target_body):
            if isinstance(stmt, (Directive, ImportDeclaration, LibraryDeclaration,
                                 ConstDeclaration, VarDeclaration, TypeDeclaration,
                                 FunctionDeclaration, MethodDeclaration)):
                insert_pos = i + 1
            else:
                break

        decl = VarDeclaration(varip=False, type=ptype, name=name, value=Identifier(name='na'))
        target_body.insert(insert_pos, decl)
        if hasattr(decl, 'parent'):
            decl.parent = outer

        self._patch_report.append({
            "type": "inject_variable",
            "kind": kind,
            "var": name,
            "line": get_lineno(control_parent)
        })
        return name

    def _get_all_block_bodies(self, node) -> List[List]:
        def body_of(n):
            if hasattr(n, 'body'):
                b = getattr(n, 'body')
                return b
            return []
        if isinstance(node, (Module, FunctionDeclaration, MethodDeclaration,
                            ForStatement, WhileStatement, ForInStatement)):
            b = body_of(node)
            return [b] if b else []
        if isinstance(node, IfStatement):
            result = []
            tb = getattr(node, 'then_body', None)
            if tb: result.append(tb)
            eb = getattr(node, 'else_body', None)
            if eb: result.append(eb)
            return result
        if isinstance(node, SwitchStatement):
            result = []
            for _, cb in getattr(node, 'cases', []):
                if cb: result.append(cb)
            db = getattr(node, 'default_body', None)
            if db: result.append(db)
            return result
        return []

    # ---------- REQUEST.SECURITY ----------
    def _fix_request_security(self, node, finding, scope_map):
        hints = getattr(finding, 'hints', {})
        if not hints.get('add_lookahead_gaps', True):
            return False
        cand = copy.deepcopy(node)
        has_gaps = any(isinstance(a, Assignment) and isinstance(a.target, Identifier) and a.target.name == 'gaps' for a in cand.args)
        has_lookahead = any(isinstance(a, Assignment) and isinstance(a.target, Identifier) and a.target.name == 'lookahead' for a in cand.args)
        if not has_gaps:
            cand.args.append(Assignment(
                target=Identifier(name='gaps'),
                value=MemberAccess(target=Identifier(name='barmerge'), member='gaps_off'),
                operator='='
            ))
        if not has_lookahead:
            cand.args.append(Assignment(
                target=Identifier(name='lookahead'),
                value=MemberAccess(target=Identifier(name='barmerge'), member='lookahead_off'),
                operator='='
            ))
        if not has_gaps or not has_lookahead:
            expr_str = AutoFixerFinal._expr_to_str_static(cand)
            temp_code = f" _ = {expr_str}"
            if not AutoFixerFinal._is_valid_pine_syntax(temp_code):
                self.fix_errors.append("⚠️ Hasil request.security tidak valid — dibatalkan")
                return False
            node.args = cand.args
            self.fix_errors.append("✅ request.security: dilengkapi gaps & lookahead")
            return True
        return False

    def _get_security_signature(self):
        if not self.type_fixer or not self.type_fixer.registry:
            return None
        try:
            func_def = self.type_fixer.registry.resolve(['request', 'security'])
            if not isinstance(func_def, BuiltinFunction) or not func_def.overloads:
                return None
            best = max(func_def.overloads, key=lambda o: len(o.params))
            opt = []
            for p in best.params:
                if getattr(p, 'optional', False):
                    dv = getattr(p, 'default', None)
                    ds = self._unparse_static(dv) if isinstance(dv, ASTNode) else str(dv) if dv else None
                    if ds is not None:
                        opt.append({'name': p.name, 'default': ds})
                    else:
                        opt.append({'name': p.name})
            return {
                'required_params': len([p for p in best.params if not getattr(p, 'optional', False)]),
                'optional_params': opt
            }
        except Exception:
            return None

    def _is_arg_of_call(self, node, parent):
        if not isinstance(parent, Call):
            return False
        for arg in parent.args:
            if arg is node:
                return True
            if isinstance(arg, Assignment) and arg.value is node:
                return True
        return False

    # ---------- VALIDASI STRUKTUR ----------
    def _ast_structure_valid(self, new_code, orig_code):
        try:
            ast_new = self._parse_ast(new_code)
            ast_old = self._parse_ast(orig_code)
            if not ast_new or not ast_old:
                return False

            def collect_with_pos(node, idx=0, parent_path=""):
                result = []
                fp = self._fingerprint(node, parent_path, idx)
                result.append((fp, idx))
                child_idx = 0
                for child in all_child_nodes(node):
                    result.extend(collect_with_pos(child, child_idx, fp))
                    child_idx += 1
                return result

            old_anchors = collect_with_pos(ast_old.root)
            new_anchors = collect_with_pos(ast_new.root)

            old_count = len(old_anchors)
            new_count = len(new_anchors)

            if new_count > old_count and (new_count - old_count) <= 4:
                pass
            elif abs(new_count - old_count) > 4:
                self.fix_errors.append("⚠️ Jumlah node berubah drastis — dibatalkan")
                return False

            i = 0
            for old_fp, old_pos in old_anchors:
                found = False
                for j in range(i, len(new_anchors)):
                    if new_anchors[j][0] == old_fp:
                        found = True
                        i = j + 1
                        break
                if not found:
                    self.fix_errors.append("⚠️ Struktur berubah — dibatalkan")
                    return False

            old_lines = orig_code.count('\n') + 1
            new_lines = new_code.count('\n') + 1
            if old_lines > 0:
                diff = abs(new_lines - old_lines)
                max_allowed = max(self._min_changes_allowed, old_lines * self._max_changes_per_file)
                if diff > max_allowed:
                    self.fix_errors.append(f"⚠️ Terlalu banyak perubahan baris ({diff}) — max {max_allowed:.1f}")
                    return False
            return True
        except Exception as e:
            self.fix_errors.append(f"⚠️ Validasi gagal: {e}")
            return False

    # ============================================================
    # UNPARSER (AMAN, KOMPATIBEL DENGAN PARSER ANDA)
    # ============================================================
    def _unparse_static(self, node, indent=0):
        IND = '    ' * indent
        if node is None:
            return ''
        if isinstance(node, Module):
            return '\n'.join(self._unparse_static(s, indent) for s in node.body)

        # Comment hanya diproses jika kelas tersedia
        if Comment is not None and isinstance(node, Comment):
            txt = node.text
            if hasattr(node, 'style') and node.style == 'block' or txt.startswith('/*'):
                return f'{IND}/*{txt}*/'
            if txt.startswith('///'):
                return f'{IND}///{txt[3:]}'
            return f'{IND}//{txt}'

        if isinstance(node, Directive):
            return f'{IND}//@{node.name}={node.value}'

        if isinstance(node, VarDeclaration):
            p = [IND]
            if getattr(node, 'varip', False):
                p.append('varip ')
            else:
                p.append('var ')
            if getattr(node, 'type', None):
                p.append(self._expr_to_str_static(node.type) + ' ')
            p.append(self._expr_to_str_static(Identifier(name=node.name)))
            if getattr(node, 'value', None):
                p.append(' = ' + self._expr_to_str_static(node.value))
            return ''.join(p)

        if isinstance(node, ConstDeclaration):
            p = [IND, 'const ']
            if getattr(node, 'type', None):
                p.append(self._expr_to_str_static(node.type) + ' ')
            p.append(f'{node.name} = {self._expr_to_str_static(node.value)}')
            return ''.join(p)

        if isinstance(node, Assignment):
            return f'{IND}{self._expr_to_str_static(node.target, -1)} {node.operator} {self._expr_to_str_static(node.value, 0)}'

        if isinstance(node, ExpressionStatement):
            return f'{IND}{self._expr_to_str_static(node.expression)}'

        if isinstance(node, IfStatement):
            r = [f'{IND}if {self._expr_to_str_static(node.condition)}']
            for s in node.then_body:
                r.append(self._unparse_static(s, indent+1))
            if node.else_body:
                r.append(f'{IND}else')
                for s in node.else_body:
                    r.append(self._unparse_static(s, indent+1))
            return '\n'.join(r)

        if isinstance(node, ForStatement):
            iterator = self._expr_to_str_static(node.iterator)
            if isinstance(node.iterable, RangeExpr):
                start = self._expr_to_str_static(node.iterable.start)
                end = self._expr_to_str_static(node.iterable.end)
                step = f" by {self._expr_to_str_static(node.iterable.step)}" if node.iterable.step else ""
                header = f"{IND}for {iterator} = {start} to {end}{step}"
            else:
                header = f"{IND}for {iterator} = {self._expr_to_str_static(node.iterable)}"
            r = [header]
            for s in node.body:
                r.append(self._unparse_static(s, indent + 1))
            return '\n'.join(r)

        if isinstance(node, ForInStatement):
            targets = ', '.join(self._expr_to_str_static(t) for t in node.targets)
            r = [f'{IND}for [{targets}] in {self._expr_to_str_static(node.iterable)}']
            for s in node.body:
                r.append(self._unparse_static(s, indent+1))
            return '\n'.join(r)

        if isinstance(node, WhileStatement):
            r = [f'{IND}while {self._expr_to_str_static(node.condition)}']
            for s in node.body:
                r.append(self._unparse_static(s, indent+1))
            return '\n'.join(r)

        if isinstance(node, SwitchStatement):
            val = self._expr_to_str_static(node.value) if node.value else ''
            r = [f'{IND}switch {val}']
            for cv, cb in node.cases:
                cv_str = self._expr_to_str_static(cv) if cv else 'default'
                r.append(f'{IND}    {cv_str} =>')
                for s in cb:
                    r.append(self._unparse_static(s, indent+2))
            if getattr(node, 'default_body', None):
                r.append(f'{IND}    =>')
                for s in node.default_body:
                    r.append(self._unparse_static(s, indent+2))
            return '\n'.join(r)

        if isinstance(node, ReturnStatement):
            return f"{IND}return {self._expr_to_str_static(node.value) if node.value else ''}".strip()

        if isinstance(node, (BreakStatement, ContinueStatement)):
            return f'{IND}{"break" if isinstance(node, BreakStatement) else "continue"}'

        if isinstance(node, FunctionDeclaration):
            p = [IND]
            if getattr(node, 'export', False):
                p.append('export ')
            p.append(self._expr_to_str_static(Identifier(name=node.name)))
            params = []
            for param in node.params:
                ps = self._param_str_static(param)
                params.append(ps)
            p.append(f'({", ".join(params)}) =>')
            r = p
            for s in node.body:
                r.append(self._unparse_static(s, indent+1))
            return '\n'.join(r)

        if isinstance(node, MethodDeclaration):
            p = [IND, 'method ']
            p.append(self._expr_to_str_static(Identifier(name=node.name)))
            params = []
            for param in node.params:
                ps = self._param_str_static(param)
                params.append(ps)
            p.append(f'({", ".join(params)}) =>')
            r = p
            for s in node.body:
                r.append(self._unparse_static(s, indent+1))
            return '\n'.join(r)

        if isinstance(node, TypeDeclaration):
            p = [IND, 'type ']
            p.append(node.name)
            r = [''.join(p)]
            for f in node.fields:
                fp = [f'{IND}    ']
                if f.type:
                    fp.append(self._expr_to_str_static(f.type) + ' ')
                fp.append(f.name)
                if f.default:
                    fp.append(f' = {self._expr_to_str_static(f.default)}')
                r.append(''.join(fp))
            return '\n'.join(r)

        if isinstance(node, EnumDeclaration):
            p = [IND, 'enum ']
            p.append(node.name)
            r = [''.join(p)]
            for v in node.values:
                vp = [f'{IND}    ']
                if isinstance(v, tuple):
                    vp.append(f'{v[0]} = {self._expr_to_str_static(v[1])}')
                else:
                    vp.append(str(v))
                r.append(''.join(vp))
            return '\n'.join(r)

        if isinstance(node, ImportDeclaration):
            return f'{IND}import {node.path}'

        if isinstance(node, LibraryDeclaration):
            return f'{IND}library {node.name or ""}'

        if isinstance(node, ExportDeclaration):
            return f'{IND}export {" ".join(node.targets)}'

        if isinstance(node, DestructuringAssignment):
            targets = ', '.join(self._expr_to_str_static(t) for t in node.targets)
            return f'{IND}[{targets}] = {self._expr_to_str_static(node.value)}'

        if isinstance(node, TupleLiteral):
            return '[' + ', '.join(self._expr_to_str_static(e) for e in node.elements) + ']'

        if isinstance(node, RangeExpr):
            s = f"{self._expr_to_str_static(node.start)} to {self._expr_to_str_static(node.end)}"
            if getattr(node, 'step', None):
                s += f" by {self._expr_to_str_static(node.step)}"
            return s

        if isinstance(node, ArrowFunction):
            params = ', '.join(self._param_str_static(p) for p in node.params)
            body = self._expr_to_str_static(node.body)
            return f'({params}) => {body}'

        if isinstance(node, GenericType):
            base = node.base
            params = ', '.join(self._expr_to_str_static(p) for p in node.params)
            return f'{base}<{params}>'

        # ColorLiteral hanya diproses jika tersedia
        if ColorLiteral is not None and isinstance(node, ColorLiteral):
            if hasattr(node, 'hex') and node.hex:
                return node.hex
            if hasattr(node, 'r') and hasattr(node, 'g') and hasattr(node, 'b'):
                return f"color.rgb({node.r}, {node.g}, {node.b})"
            return "color.na"

        if isinstance(node, TypeField):
            parts = []
            if f.type:
                parts.append(self._expr_to_str_static(node.type) + ' ')
            parts.append(node.name)
            if node.default:
                parts.append(f" = {self._expr_to_str_static(node.default)}")
            return IND + ''.join(parts)

        # FALLBACK AMAN
        node_type = type(node).__name__
        if node_type not in self._unsupported_nodes:
            self._unsupported_nodes.add(node_type)
        if hasattr(node, 'original_text'):
            return getattr(node, 'original_text')
        return f"{IND}/* UNSUPPORTED:{node_type} — bagian ini tidak diubah */"

    # ============================================================
    # EXPR TO STR
    # ============================================================
    @staticmethod
    def _expr_to_str_static(node, parent_prec=0):
        P = AutoFixerFinal.PRECEDENCE
        if node is None:
            return 'na'
        if isinstance(node, IntegerLiteral):
            return str(node.value)
        if isinstance(node, FloatLiteral):
            return str(node.value)
        if isinstance(node, StringLiteral):
            return f'"{AutoFixerFinal._escape_string(node.value)}"'
        if isinstance(node, BoolLiteral):
            return 'true' if node.value else 'false'
        if isinstance(node, Identifier):
            return node.name
        if isinstance(node, QualifiedName):
            return '.'.join(node.parts)
        if isinstance(node, MemberAccess):
            return f"{AutoFixerFinal._expr_to_str_static(node.target)}.{node.member}"
        if isinstance(node, Call):
            args = ', '.join(AutoFixerFinal._expr_to_str_static(a) for a in node.args)
            return f"{AutoFixerFinal._expr_to_str_static(node.func)}({args})"
        if isinstance(node, Assignment):
            prec = P['assignment']
            left = AutoFixerFinal._expr_to_str_static(node.target, prec)
            right = AutoFixerFinal._expr_to_str_static(node.value, prec+1)
            s = f"{left} {node.operator} {right}"
            return f'({s})' if parent_prec > prec else s
        if isinstance(node, BinaryOp):
            op = node.operator
            prec = P.get(op, 5)
            left = AutoFixerFinal._expr_to_str_static(node.left, prec+1)
            right = AutoFixerFinal._expr_to_str_static(node.right, prec+1)
            s = f"{left} {op} {right}"
            return f'({s})' if parent_prec > prec else s
        if isinstance(node, UnaryOp):
            prec = P['unary']
            oper = AutoFixerFinal._expr_to_str_static(node.operand, prec+1)
            s = node.operator + oper
            return f'({s})' if parent_prec > prec else s
        if isinstance(node, TernaryOp):
            prec = P['ternary']
            cond = AutoFixerFinal._expr_to_str_static(node.condition, prec+1)
            t = AutoFixerFinal._expr_to_str_static(node.then_expr, prec+1)
            e = AutoFixerFinal._expr_to_str_static(node.else_expr, prec+1)
            s = f"{cond} ? {t} : {e}"
            return f'({s})' if parent_prec > prec else s
        if isinstance(node, Index):
            return f"{AutoFixerFinal._expr_to_str_static(node.target)}[{AutoFixerFinal._expr_to_str_static(node.index)}]"
        if isinstance(node, RangeExpr):
            s = f"{AutoFixerFinal._expr_to_str_static(node.start)} to {AutoFixerFinal._expr_to_str_static(node.end)}"
            if getattr(node, 'step', None):
                s += f" by {AutoFixerFinal._expr_to_str_static(node.step)}"
            return s
        if isinstance(node, TupleLiteral):
            return '[' + ', '.join(AutoFixerFinal._expr_to_str_static(e) for e in node.elements) + ']'
        if isinstance(node, ArrowFunction):
            params = ', '.join(AutoFixerFinal._param_str_static(p) for p in node.params)
            body = AutoFixerFinal._expr_to_str_static(node.body)
            return f'({params}) => {body}'
        if isinstance(node, GenericType):
            base = node.base
            params = ', '.join(AutoFixerFinal._expr_to_str_static(p) for p in node.params)
            return f'{base}<{params}>'
        if ColorLiteral is not None and isinstance(node, ColorLiteral):
            if hasattr(node, 'hex') and node.hex:
                return node.hex
            if hasattr(node, 'r') and hasattr(node, 'g') and hasattr(node, 'b'):
                return f"color.rgb({node.r}, {node.g}, {node.b})"
            return "color.na"
        node_type = type(node).__name__
        return f"/* expr: {node_type} — tidak dapat dievaluasi */"

    @staticmethod
    def _escape_string(s: str) -> str:
        try:
            escaped = s.encode('unicode_escape').decode('ascii')
            escaped = escaped.replace('"', '\\"')
            return escaped
        except Exception:
            return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')

    @staticmethod
    def _default_to_ast_safe(val):
        if isinstance(val, ASTNode):
            return val
        if isinstance(val, str):
            if '.' in val:
                a, b = val.split('.', 1)
                return MemberAccess(target=Identifier(name=a), member=b)
            return StringLiteral(value=val)
        if isinstance(val, bool):
            return BoolLiteral(value=val)
        if isinstance(val, int):
            return IntegerLiteral(value=val)
        if isinstance(val, float):
            return FloatLiteral(value=val)
        return Identifier(name=str(val))

    @staticmethod
    def _is_valid_pine_syntax(code: str) -> bool:
        try:
            from engine.parser import PineAST
            ast = PineAST(code)
            if hasattr(ast, 'errors') and ast.errors:
                return False
            return True
        except Exception:
            return False

    @staticmethod
    def _type_to_str_qualified_static(pine_type) -> Optional[str]:
        if not pine_type:
            return None
        qual = ''
        base = ''
        if hasattr(pine_type, 'qualifier'):
            q = pine_type.qualifier
            if q in (SERIES, 'series', 'SERIES'):
                qual = 'series '
            elif q in (CONST, 'const', 'CONST'):
                qual = 'const '
            elif q in (INPUT, 'input', 'INPUT'):
                qual = 'input '
            elif q in (SIMPLE, 'simple', 'SIMPLE'):
                qual = ''
            elif isinstance(q, str):
                qual = q + ' '
        if hasattr(pine_type, 'base_type'):
            bt = pine_type.base_type
            if isinstance(bt, str):
                base = bt
            elif hasattr(bt, 'name'):
                base = bt.name
            else:
                base = str(bt).split('.')[-1].lower()
        elif hasattr(pine_type, 'name'):
            base = pine_type.name
        elif isinstance(pine_type, str):
            base = pine_type
        else:
            base = str(pine_type).split('.')[-1].lower()
        NORM = {
            'float':'float', 'int':'int', 'bool':'bool', 'string':'string', 'color':'color',
            'box':'box', 'label':'label', 'line':'line', 'linefill':'linefill', 'polyline':'polyline',
            'table':'table', 'hline':'hline', 'matrix':'matrix', 'array':'array', 'map':'map', 'void':'void'
        }
        base = NORM.get(base.lower().strip('_'), base)
        return (qual + base).strip()

    @staticmethod
    def _param_str_static(param):
        if isinstance(param, dict):
            t = AutoFixerFinal._expr_to_str_static(param.get('type')) if param.get('type') else ''
            name = param.get('name', '')
            default = param.get('default')
            s = f"{t} {name}" if t else name
            if default is not None:
                s += f" = {AutoFixerFinal._expr_to_str_static(default)}"
            return s
        if hasattr(param, 'name'):
            name = param.name
            typ = AutoFixerFinal._expr_to_str_static(param.type) if hasattr(param, 'type') and param.type else ''
            default = getattr(param, 'default', None)
            s = f"{typ} {name}" if typ else name
            if default is not None:
                s += f" = {AutoFixerFinal._expr_to_str_static(default)}"
            return s
        return str(param)

    def _get_func_name(self, node):
        if isinstance(node, Identifier):
            return node.name
        if isinstance(node, QualifiedName):
            return '.'.join(node.parts)
        if isinstance(node, MemberAccess):
            t = self._get_func_name(node.target)
            return f"{t}.{node.member}" if t else None
        return None

    def _is_valid_pine(self, code):
        try:
            from engine.parser import PineAST
            ast = PineAST(code)
            if hasattr(ast, 'errors') and ast.errors:
                return False
            return True
        except Exception:
            return False

    def _re_extract(self, code):
        try:
            from engine.parser import PineAST
            from engine.extractor import FeatureExtractor
            ast = PineAST(code)
            if hasattr(ast, 'errors') and ast.errors:
                return []
            return FeatureExtractor(ast.root, code).extract_all()
        except Exception:
            return []

    def _generate_diff(self, orig, patched, path):
        return ''.join(difflib.unified_diff(
            orig.splitlines(keepends=True),
            patched.splitlines(keepends=True),
            f'a/{path}', f'b/{path}'
        ))

    @staticmethod
    def main():
        if len(sys.argv) < 2:
            print("Usage: python3 auto_fixer.py <file.pine> [--dry-run] [--report-only] [--json-output report.json] [--strict]")
            sys.exit(1)

        file_path = sys.argv[1]
        dry_run = '--dry-run' in sys.argv
        report_only = '--report-only' in sys.argv
        strict = '--strict' in sys.argv
        json_output = None
        for i, arg in enumerate(sys.argv):
            if arg == '--json-output' and i+1 < len(sys.argv):
                json_output = sys.argv[i+1]

        if not os.path.isfile(file_path):
            print(f"❌ File tidak ditemukan: {file_path}")
            sys.exit(1)

        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        registry = None
        if TYPE_AWARE_AVAILABLE:
            try:
                registry = BuiltinRegistry()
                print("✅ Registry bawaan dimuat dari engine.pine_builtins")
            except Exception as e:
                print(f"⚠️ Gagal memuat registry bawaan: {e}")

        try:
            from engine.parser import PineAST
            from engine.extractor import FeatureExtractor
            ast = PineAST(code)
            if hasattr(ast, 'errors') and ast.errors:
                print(f"❌ AST mengandung error, tidak bisa diproses: {ast.errors}")
                sys.exit(1)
            features = FeatureExtractor(ast.root, code).extract_all()
        except Exception as e:
            print(f"❌ Gagal ekstraksi fitur: {e}")
            features = []

        fixer = AutoFixerFinal(registry=registry, strict=strict)
        patched, count = fixer.fix(file_path, code, features=features, dry_run=dry_run,
                                   auto_confirm=False, json_output=json_output, report_only=report_only)

        if report_only:
            print("\n✅ Laporan analisis selesai.")
        elif patched is None:
            print("ℹ️ Tidak ada perbaikan yang diperlukan atau dibatalkan.")
        elif dry_run:
            print(f"\n✅ {count} perbaikan siap diterapkan (dry-run)")
        else:
            print(f"\n✅ {count} perbaikan berhasil diterapkan.")

if __name__ == "__main__":
    AutoFixerFinal.main()
