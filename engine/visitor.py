#!/usr/bin/env python3
"""
AST Visitor Pattern — Base class untuk detector.
"""
from abc import ABC, abstractmethod
from typing import Any
from engine.parser import (
    ASTNode, Module, VarDeclaration, ConstDeclaration,
    FunctionDeclaration, MethodDeclaration, IfStatement,
    ForStatement, ForInStatement, WhileStatement, SwitchStatement,
    ReturnStatement, Call, Assignment, ExpressionStatement,
    Identifier, QualifiedName, MemberAccess
)
from engine.ast_utils import get_children


class ASTVisitor(ABC):
    """Base visitor dengan default no-op untuk semua node."""
    
    def visit(self, node: ASTNode) -> Any:
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ASTNode) -> Any:
        for child in get_children(node):
            self.visit(child)

    def visit_Module(self, node: Module):
        self.generic_visit(node)

    def visit_VarDeclaration(self, node: VarDeclaration):
        self.generic_visit(node)

    def visit_ConstDeclaration(self, node: ConstDeclaration):
        self.generic_visit(node)

    def visit_FunctionDeclaration(self, node: FunctionDeclaration):
        self.generic_visit(node)

    def visit_MethodDeclaration(self, node: MethodDeclaration):
        self.generic_visit(node)

    def visit_IfStatement(self, node: IfStatement):
        self.generic_visit(node)

    def visit_ForStatement(self, node: ForStatement):
        self.generic_visit(node)

    def visit_ForInStatement(self, node: ForInStatement):
        self.generic_visit(node)

    def visit_WhileStatement(self, node: WhileStatement):
        self.generic_visit(node)

    def visit_SwitchStatement(self, node: SwitchStatement):
        self.generic_visit(node)

    def visit_ReturnStatement(self, node: ReturnStatement):
        self.generic_visit(node)

    def visit_Call(self, node: Call):
        self.generic_visit(node)

    def visit_Assignment(self, node: Assignment):
        self.generic_visit(node)

    def visit_ExpressionStatement(self, node: ExpressionStatement):
        self.generic_visit(node)
