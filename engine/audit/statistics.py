#!/usr/bin/env python3
"""StatisticsVisitor — Traversal AST publik untuk menghitung statistik."""
from engine.visitor import ASTVisitor
from engine.parser import (
    TypeDeclaration, MethodDeclaration, FunctionDeclaration,
    VarDeclaration, SwitchStatement, Call, IfStatement,
    ForStatement, WhileStatement, ReturnStatement,
    Identifier, MemberAccess
)

class StatisticsVisitor(ASTVisitor):
    """Visitor publik yang menghitung statistik AST dalam satu traversal."""

    def __init__(self):
        self.total_nodes = 0
        self.unique_types = set()
        self.type_count = 0
        self.method_count = 0
        self.func_count = 0
        self.var_count = 0
        self.switch_count = 0
        self.if_count = 0
        self.for_count = 0
        self.while_count = 0
        self.return_count = 0
        self.call_count = 0
        self.call_names = []
        self.max_depth = 0
        self._current_depth = 0

    def generic_visit(self, node):
        self.total_nodes += 1
        self.unique_types.add(type(node).__name__)
        self._current_depth += 1
        self.max_depth = max(self.max_depth, self._current_depth)
        super().generic_visit(node)
        self._current_depth -= 1

    def visit_TypeDeclaration(self, node):
        self.type_count += 1
        self.generic_visit(node)

    def visit_MethodDeclaration(self, node):
        self.method_count += 1
        self.generic_visit(node)

    def visit_FunctionDeclaration(self, node):
        self.func_count += 1
        self.generic_visit(node)

    def visit_VarDeclaration(self, node):
        self.var_count += 1
        self.generic_visit(node)

    def visit_SwitchStatement(self, node):
        self.switch_count += 1
        self.generic_visit(node)

    def visit_IfStatement(self, node):
        self.if_count += 1
        self.generic_visit(node)

    def visit_ForStatement(self, node):
        self.for_count += 1
        self.generic_visit(node)

    def visit_WhileStatement(self, node):
        self.while_count += 1
        self.generic_visit(node)

    def visit_ReturnStatement(self, node):
        self.return_count += 1
        self.generic_visit(node)

    def visit_Call(self, node):
        self.call_count += 1
        if isinstance(node.func, Identifier):
            self.call_names.append(node.func.name)
        elif isinstance(node.func, MemberAccess):
            path = []
            cur = node.func
            while isinstance(cur, MemberAccess):
                path.append(cur.member)
                cur = cur.target
            if isinstance(cur, Identifier):
                path.append(cur.name)
            self.call_names.append('.'.join(reversed(path)))
        self.generic_visit(node)

    def to_dict(self) -> dict:
        return {
            'total_nodes': self.total_nodes,
            'unique_types': len(self.unique_types),
            'types': self.type_count,
            'methods': self.method_count,
            'functions': self.func_count,
            'variables': self.var_count,
            'switches': self.switch_count,
            'if_statements': self.if_count,
            'for_loops': self.for_count,
            'while_loops': self.while_count,
            'returns': self.return_count,
            'calls': self.call_count,
            'max_depth': self.max_depth,
        }
