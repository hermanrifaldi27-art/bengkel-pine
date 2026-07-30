#!/usr/bin/env python3
"""
Pine Semantic Analyzer v5.0 — Complete builtins, type preservation
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from engine.parser import (
    ASTNode, Module, VarDeclaration, ConstDeclaration,
    FunctionDeclaration, MethodDeclaration, Identifier,
    IfStatement, ForStatement, ForInStatement, WhileStatement,
    SwitchStatement, ReturnStatement, ExpressionStatement,
    GenericType, ArrowFunction, TypeDeclaration, EnumDeclaration,
    IntegerLiteral, FloatLiteral, BoolLiteral, StringLiteral,
    MemberAccess, QualifiedName, BinaryOp, UnaryOp, TernaryOp,
    SourceSpan, Call, Assignment
)
from engine.ast_utils import get_children
from engine.types import (
    PineType, TypeKind, TYPE_NA, TYPE_INT, TYPE_FLOAT, TYPE_BOOL,
    TYPE_STRING, TYPE_VOID, TYPE_COLOR
)
from engine.evaluator import ConstantEvaluator, ConstantValue
from engine.pine_builtins import BuiltinRegistry
from engine.diagnostics import DiagnosticEngine

@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str
    node: ASTNode = field(repr=False)
    scope: 'Scope' = field(repr=False)
    value: Any = None
    type: Optional[PineType] = None

class Scope:
    def __init__(self, parent: Optional[Scope] = None, name: str = "global", owner_node: Optional[ASTNode] = None):
        self.parent = parent
        self.name = name
        self.owner_node = owner_node
        self.symbols: Dict[str, Symbol] = {}
        self.children: List[Scope] = []

    def define(self, name: str, kind: str, node: ASTNode,
               value: Any = None, type_: Optional[PineType] = None) -> Symbol:
        if name in self.symbols:
            import sys
            print(f"⚠️  Warning: redefinition of '{name}' in scope '{self.name}'", file=sys.stderr)
        sym = Symbol(name=name, kind=kind, node=node, scope=self, value=value, type=type_)
        self.symbols[name] = sym
        return sym

    def resolve(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.resolve(name)
        return None

    def create_child(self, name: str = "", owner_node: Optional[ASTNode] = None) -> 'Scope':
        child = Scope(parent=self, name=name, owner_node=owner_node)
        self.children.append(child)
        return child

class SemanticAnalyzer:
    def __init__(self, diagnostics: Optional[DiagnosticEngine] = None):
        self.global_scope = Scope(name="global")
        self.current_scope = self.global_scope
        self.parent_map: Dict[int, ASTNode] = {}
        self.scope_of_node: Dict[int, Scope] = {}
        self.node_scope_owner: Dict[int, Scope] = {}
        self.const_values: Dict[str, ConstantValue] = {}
        self.enum_values: Dict[str, Any] = {}
        self.builtin = BuiltinRegistry()
        self.evaluator = ConstantEvaluator(self.const_values, self.builtin, self.enum_values)
        self.diagnostics = diagnostics or DiagnosticEngine()

    def analyze(self, ast: Module) -> Scope:
        self._walk(ast, None)
        return self.global_scope

    def _resolve_in_scope(self, name: str, scope: Scope) -> Optional[Symbol]:
        return scope.resolve(name)

    def _walk(self, node: ASTNode, parent: Optional[ASTNode]):
        if node is None:
            return
        self.parent_map[id(node)] = parent

        new_scope = None
        if isinstance(node, (FunctionDeclaration, MethodDeclaration)):
            self.current_scope.define(node.name, 'function' if isinstance(node, FunctionDeclaration) else 'method', node, type_=TYPE_VOID)
            new_scope = self.current_scope.create_child(node.name, owner_node=node)
            self.node_scope_owner[id(node)] = new_scope
            self.scope_of_node[id(node)] = self.current_scope
            self.current_scope = new_scope
            for p in node.params:
                if p.get('name'):
                    param_type = PineType.from_ast(p.get('type')) if p.get('type') else None
                    self.current_scope.define(p['name'], 'param', node, type_=param_type)

        self.scope_of_node[id(node)] = self.current_scope

        if isinstance(node, VarDeclaration):
            var_type = PineType.from_ast(node.type) if node.type else None
            if var_type is None and node.value:
                inferred = self._infer_type(node.value)
                if inferred:
                    var_type = inferred
            self.current_scope.define(node.name, 'var', node, type_=var_type)
        elif isinstance(node, ConstDeclaration):
            scope = self.scope_of_node.get(id(node), self.global_scope)
            val = self._evaluate_in_scope(node.value, scope)
            const_type = None
            if isinstance(val, ConstantValue):
                const_type = val.type
                self.current_scope.define(node.name, 'const', node, value=val, type_=const_type)
                self.const_values[node.name] = val
            else:
                self.current_scope.define(node.name, 'const', node, value=val, type_=const_type)
                self.const_values[node.name] = ConstantValue(val) if val is not None else ConstantValue(None, TYPE_NA)
        elif isinstance(node, TypeDeclaration):
            self.current_scope.define(node.name, 'type', node)
        elif isinstance(node, EnumDeclaration):
            self.current_scope.define(node.name, 'enum', node)
            enum_members = {}
            for v in node.values:
                if isinstance(v, tuple) and len(v) == 2:
                    enum_name = v[0]
                    enum_value = v[1]
                    enum_members[enum_name] = ConstantValue(enum_name, TYPE_STRING)
                    self.const_values[enum_name] = ConstantValue(enum_value.value if hasattr(enum_value, 'value') else enum_value, TYPE_STRING)
                elif isinstance(v, str):
                    enum_members[v] = ConstantValue(v, TYPE_STRING)
            self.enum_values[node.name] = enum_members

        for child in get_children(node):
            self._walk(child, node)

        if new_scope:
            self.current_scope = self.current_scope.parent

    def _evaluate_in_scope(self, node: ASTNode, scope: Scope) -> Any:
        resolver = lambda name, s: s.resolve(name)
        return self.evaluator.evaluate_with_scope(node, resolver, scope)

    def _infer_type(self, node: ASTNode) -> Optional[PineType]:
        if isinstance(node, IntegerLiteral):
            return TYPE_INT
        if isinstance(node, FloatLiteral):
            return TYPE_FLOAT
        if isinstance(node, BoolLiteral):
            return TYPE_BOOL
        if isinstance(node, StringLiteral):
            return TYPE_STRING
        if isinstance(node, Identifier):
            if node.name == 'na':
                return TYPE_NA
            sym = self.current_scope.resolve(node.name)
            if sym:
                return sym.type
        if isinstance(node, BinaryOp):
            left = self._infer_type(node.left)
            right = self._infer_type(node.right)
            if left and right:
                if left.kind == TypeKind.FLOAT or right.kind == TypeKind.FLOAT:
                    return TYPE_FLOAT
                if left.kind == TypeKind.INT or right.kind == TypeKind.INT:
                    return TYPE_INT
                return left
        return None

    def evaluate_constant(self, node: ASTNode, scope: Optional[Scope] = None) -> Any:
        if scope is None:
            scope = self.get_scope_of(node)
        return self._evaluate_in_scope(node, scope)

    def get_scope_of(self, node: ASTNode) -> Scope:
        return self.scope_of_node.get(id(node), self.global_scope)

    def get_enclosing_function(self, node: ASTNode) -> Optional[ASTNode]:
        current = self.parent_map.get(id(node))
        while current is not None:
            if isinstance(current, (FunctionDeclaration, MethodDeclaration)):
                return current
            current = self.parent_map.get(id(current))
        return None

    def get_symbol(self, name: str) -> Optional[Symbol]:
        return self.global_scope.resolve(name)

_analyzer_cache = None

def analyze(ast: Module) -> SemanticAnalyzer:
    global _analyzer_cache
    analyzer = SemanticAnalyzer()
    analyzer.analyze(ast)
    _analyzer_cache = analyzer
    return analyzer

def get_analyzer() -> Optional[SemanticAnalyzer]:
    return _analyzer_cache
