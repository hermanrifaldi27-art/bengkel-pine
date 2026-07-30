#!/usr/bin/env python3
"""
AST Utilities — get_children shared across parser, extractor, semantic.
"""
from typing import List
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
    ExpressionStatement, Directive
)

def get_children(node: ASTNode) -> List[ASTNode]:
    children = []
    if node is None: return children
    if isinstance(node, Module): children.extend(node.body)
    elif isinstance(node, (IntegerLiteral, FloatLiteral, StringLiteral, BoolLiteral,
                           Identifier, BreakStatement, ContinueStatement, Directive)): pass
    elif isinstance(node, QualifiedName): pass
    elif isinstance(node, UnaryOp): children.append(node.operand)
    elif isinstance(node, BinaryOp): children.extend([node.left, node.right])
    elif isinstance(node, TernaryOp): children.extend([node.condition, node.then_expr, node.else_expr])
    elif isinstance(node, Call):
        children.append(node.func)
        children.extend(node.args)
    elif isinstance(node, Index):
        children.extend([node.target, node.index])
    elif isinstance(node, MemberAccess): children.append(node.target)
    elif isinstance(node, RangeExpr):
        children.extend([node.start, node.end])
        if node.step: children.append(node.step)
    elif isinstance(node, TupleLiteral): children.extend(node.elements)
    elif isinstance(node, DestructuringAssignment):
        children.extend(node.targets)
        children.append(node.value)
    elif isinstance(node, GenericType): children.extend(node.params)
    elif isinstance(node, ArrowFunction):
        if node.body: children.append(node.body)
        for p in node.params:
            if p.get('type'): children.append(p['type'])
            if p.get('default'): children.append(p['default'])
    elif isinstance(node, TypeField):
        if node.type: children.append(node.type)
        if node.default: children.append(node.default)
    elif isinstance(node, VarDeclaration):
        if node.type: children.append(node.type)
        if node.value: children.append(node.value)
    elif isinstance(node, ConstDeclaration): children.append(node.value)
    elif isinstance(node, TypeDeclaration): children.extend(node.fields)
    elif isinstance(node, EnumDeclaration):
        for v in node.values:
            if isinstance(v, tuple) and len(v) == 2: children.append(v[1])
    elif isinstance(node, MethodDeclaration):
        children.extend(node.body)
        for p in node.params:
            if p.get('type'): children.append(p['type'])
            if p.get('default'): children.append(p['default'])
    elif isinstance(node, FunctionDeclaration):
        children.extend(node.body)
        for p in node.params:
            if p.get('type'): children.append(p['type'])
            if p.get('default'): children.append(p['default'])
    elif isinstance(node, ImportDeclaration): pass
    elif isinstance(node, LibraryDeclaration): pass
    elif isinstance(node, ExportDeclaration): pass
    elif isinstance(node, Assignment):
        children.append(node.target)
        children.append(node.value)
    elif isinstance(node, IfStatement):
        children.append(node.condition)
        children.extend(node.then_body)
        children.extend(node.else_body)
    elif isinstance(node, ForStatement):
        children.append(node.iterator)
        children.append(node.iterable)
        children.extend(node.body)
    elif isinstance(node, ForInStatement):
        children.extend(node.targets)
        children.append(node.iterable)
        children.extend(node.body)
    elif isinstance(node, WhileStatement):
        children.append(node.condition)
        children.extend(node.body)
    elif isinstance(node, SwitchStatement):
        if node.value: children.append(node.value)
        for _, b in node.cases: children.extend(b)
        children.extend(node.default_body)
    elif isinstance(node, ReturnStatement):
        if node.value: children.append(node.value)
    elif isinstance(node, ExpressionStatement): children.append(node.expression)
    return children
