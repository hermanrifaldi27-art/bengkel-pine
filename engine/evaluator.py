#!/usr/bin/env python3
"""
Constant Evaluator v3.0 — Menggunakan BuiltinRegistry lengkap
"""
from typing import Any, Optional, Dict, Set
from engine.parser import (
    ASTNode, IntegerLiteral, FloatLiteral, BoolLiteral, StringLiteral,
    Identifier, QualifiedName, MemberAccess, BinaryOp, UnaryOp, TernaryOp
)
from engine.types import (
    PineType, TypeKind, TYPE_NA, TYPE_INT, TYPE_FLOAT, TYPE_BOOL, TYPE_STRING,
    TYPE_COLOR
)
from engine.pine_builtins import BuiltinRegistry, ConstantValue, BuiltinFunction, Namespace

class ConstantEvaluator:
    def __init__(self, const_values: Dict[str, Any], builtin: BuiltinRegistry,
                 enum_values: Optional[Dict[str, Any]] = None):
        self.const_values = const_values  # ConstantValue objects
        self.builtin = builtin
        self.enum_values = enum_values or {}
        self.visited: Set[int] = set()
        self.symbol_visited: Set[str] = set()

    def evaluate(self, node: ASTNode) -> Any:
        if id(node) in self.visited:
            return node
        self.visited.add(id(node))
        try:
            result = self._eval(node)
        except Exception:
            result = node
        self.visited.discard(id(node))
        return result

    def evaluate_with_scope(self, node: ASTNode, scope_resolver, scope) -> Any:
        if id(node) in self.visited:
            return node
        self.visited.add(id(node))
        try:
            result = self._eval_with_scope(node, scope_resolver, scope)
        except Exception:
            result = node
        self.visited.discard(id(node))
        return result

    def _eval(self, node: ASTNode) -> Any:
        if isinstance(node, IntegerLiteral):
            return ConstantValue(node.value, TYPE_INT)
        if isinstance(node, FloatLiteral):
            return ConstantValue(node.value, TYPE_FLOAT)
        if isinstance(node, BoolLiteral):
            return ConstantValue(node.value, TYPE_BOOL)
        if isinstance(node, StringLiteral):
            return ConstantValue(node.value, TYPE_STRING)
        if isinstance(node, Identifier):
            if node.name == 'na':
                return ConstantValue(None, TYPE_NA)
            # Cek konstanta user
            if node.name in self.const_values:
                return self._resolve_const(node.name)
            # Cek enum
            if node.name in self.enum_values:
                return ConstantValue(node.name, TYPE_STRING)
            # Cek global series (open, high, dll)
            if hasattr(self.builtin, 'global_series') and node.name in self.builtin.global_series:
                return ConstantValue(node.name, self.builtin.global_series[node.name])
            return node
        if isinstance(node, QualifiedName):
            # Cek builtin
            val = self.builtin.resolve(node.parts)
            if val is not None:
                return val  # ConstantValue atau BuiltinFunction
            # Cek konstanta user dengan nama lengkap
            full_name = '.'.join(node.parts)
            if full_name in self.const_values:
                return self._resolve_const(full_name)
            # Cek enum member: Side.Long
            if len(node.parts) == 2:
                enum_name = node.parts[0]
                member_name = node.parts[1]
                if enum_name in self.enum_values:
                    return ConstantValue(member_name, TYPE_STRING)
            return node
        if isinstance(node, MemberAccess):
            target = self.evaluate(node.target)
            if isinstance(target, Namespace):
                return target.get(node.member) or node
            if isinstance(target, ConstantValue) and hasattr(target, 'members'):
                return target.members.get(node.member, node)
            return node
        if isinstance(node, BinaryOp):
            left = self.evaluate(node.left)
            right = self.evaluate(node.right)
            if isinstance(left, ConstantValue) and isinstance(right, ConstantValue):
                return self._apply_binary_op(left, right, node.operator)
            return node
        if isinstance(node, UnaryOp):
            operand = self.evaluate(node.operand)
            return self._apply_unary_op(node.operator, operand)
        if isinstance(node, TernaryOp):
            cond = self.evaluate(node.condition)
            if isinstance(cond, ConstantValue) and cond.type.kind == TypeKind.BOOL:
                return self.evaluate(node.then_expr if cond.value else node.else_expr)
            return node
        return node

    def _eval_with_scope(self, node: ASTNode, scope_resolver, scope) -> Any:
        if isinstance(node, (IntegerLiteral, FloatLiteral, BoolLiteral, StringLiteral)):
            return self._eval(node)
        if isinstance(node, Identifier):
            if node.name == 'na':
                return ConstantValue(None, TYPE_NA)
            sym = scope_resolver(node.name, scope)
            if sym and hasattr(sym, 'value') and sym.value is not None:
                if isinstance(sym.value, ConstantValue):
                    return sym.value
                return ConstantValue(sym.value, sym.type if hasattr(sym, 'type') else None)
            return self._eval(node)
        if isinstance(node, (QualifiedName, MemberAccess)):
            return self._eval(node)
        if isinstance(node, BinaryOp):
            left = self._eval_with_scope(node.left, scope_resolver, scope)
            right = self._eval_with_scope(node.right, scope_resolver, scope)
            if isinstance(left, ConstantValue) and isinstance(right, ConstantValue):
                return self._apply_binary_op(left, right, node.operator)
            return node
        if isinstance(node, UnaryOp):
            operand = self._eval_with_scope(node.operand, scope_resolver, scope)
            return self._apply_unary_op(node.operator, operand)
        if isinstance(node, TernaryOp):
            cond = self._eval_with_scope(node.condition, scope_resolver, scope)
            if isinstance(cond, ConstantValue) and cond.type.kind == TypeKind.BOOL:
                return self._eval_with_scope(node.then_expr if cond.value else node.else_expr, scope_resolver, scope)
            return node
        return self._eval(node)

    def _apply_unary_op(self, op: str, operand: Any) -> Any:
        if not isinstance(operand, ConstantValue):
            return operand
        try:
            if op == '-':
                if operand.type.kind in (TypeKind.INT, TypeKind.FLOAT):
                    return ConstantValue(-operand.value, operand.type)
            if op == '+':
                if operand.type.kind in (TypeKind.INT, TypeKind.FLOAT):
                    return operand
            if op == 'not':
                if operand.type.kind == TypeKind.BOOL:
                    return ConstantValue(not operand.value, TYPE_BOOL)
        except Exception:
            pass
        return operand

    def _resolve_const(self, name: str) -> Any:
        if name in self.symbol_visited:
            return ConstantValue(None, TYPE_NA)
        self.symbol_visited.add(name)
        val = self.const_values.get(name)
        if val is None:
            self.symbol_visited.discard(name)
            return ConstantValue(None, TYPE_NA)
        if isinstance(val, ConstantValue):
            self.symbol_visited.discard(name)
            return val
        if isinstance(val, (int, float, bool, str)):
            self.symbol_visited.discard(name)
            return ConstantValue(val)
        self.symbol_visited.discard(name)
        return val

    def _apply_binary_op(self, left: ConstantValue, right: ConstantValue, op: str) -> Any:
        lv, rv = left.value, right.value
        try:
            if op in ('+', '-', '*', '/', '%', '**'):
                if op == '+': res = lv + rv
                elif op == '-': res = lv - rv
                elif op == '*': res = lv * rv
                elif op == '/': res = lv / rv if rv != 0 else None
                elif op == '%': res = lv % rv if rv != 0 else None
                elif op == '**': res = lv ** rv
                if isinstance(res, float) or left.type.kind == TypeKind.FLOAT or right.type.kind == TypeKind.FLOAT:
                    return ConstantValue(float(res) if res is not None else None, TYPE_FLOAT)
                return ConstantValue(int(res) if res is not None else None, TYPE_INT)
            if op in ('==', '!=', '>', '<', '>=', '<='):
                if op == '==': res = lv == rv
                elif op == '!=': res = lv != rv
                elif op == '>': res = lv > rv
                elif op == '<': res = lv < rv
                elif op == '>=': res = lv >= rv
                elif op == '<=': res = lv <= rv
                return ConstantValue(res, TYPE_BOOL)
            if op in ('and', 'or'):
                if op == 'and': res = lv and rv
                elif op == 'or': res = lv or rv
                return ConstantValue(res, TYPE_BOOL)
            if op in ('&', '|', '^', '<<', '>>'):
                if op == '&': res = lv & rv
                elif op == '|': res = lv | rv
                elif op == '^': res = lv ^ rv
                elif op == '<<': res = lv << rv
                elif op == '>>': res = lv >> rv
                return ConstantValue(res, TYPE_INT)
        except Exception:
            pass
        return None
