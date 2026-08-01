#!/usr/bin/env python3
"""
PineAST v4.0.2 — Pratt Parser untuk Pine Script v6
FIX: enum/type declaration dengan indentasi tidak terparse
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Union, Tuple

MAX_CODE_SIZE = 10 * 1024 * 1024
MAX_NUMBER_LENGTH = 50
MAX_PARSE_DEPTH = 512

@dataclass
class SourceSpan:
    start_line: int
    start_col: int
    end_line: int
    end_col: int

class ASTNode:
    span: Optional[SourceSpan] = None

# AST nodes (persis sama dengan v4.0.1, tidak diubah)
@dataclass
class Module(ASTNode):
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class IntegerLiteral(ASTNode): value: int
@dataclass
class FloatLiteral(ASTNode): value: float
@dataclass
class StringLiteral(ASTNode): value: str
@dataclass
class BoolLiteral(ASTNode): value: bool
@dataclass
class Identifier(ASTNode): name: str
@dataclass
class QualifiedName(ASTNode): parts: List[str]
@dataclass
class UnaryOp(ASTNode): operator: str; operand: ASTNode
@dataclass
class BinaryOp(ASTNode): operator: str; left: ASTNode; right: ASTNode
@dataclass
class TernaryOp(ASTNode): condition: ASTNode; then_expr: ASTNode; else_expr: ASTNode
@dataclass
class Call(ASTNode): func: ASTNode; args: List[ASTNode] = field(default_factory=list)
@dataclass
class Index(ASTNode): target: ASTNode; index: ASTNode
@dataclass
class MemberAccess(ASTNode): target: ASTNode; member: str
@dataclass
class RangeExpr(ASTNode): start: ASTNode; end: ASTNode; step: Optional[ASTNode] = None
@dataclass
class TupleLiteral(ASTNode): elements: List[ASTNode]
@dataclass
class DestructuringAssignment(ASTNode): targets: List[ASTNode]; value: ASTNode
@dataclass
class GenericType(ASTNode): base: str; params: List[ASTNode]
@dataclass
class ArrowFunction(ASTNode): params: List[Dict[str, Optional[ASTNode]]]; body: ASTNode
@dataclass
class TypeField(ASTNode): name: str; type: Optional[ASTNode]; default: Optional[ASTNode]

@dataclass
class VarDeclaration(ASTNode): varip: bool; type: Optional[ASTNode]; name: str; value: Optional[ASTNode]
@dataclass
class ConstDeclaration(ASTNode): name: str; value: ASTNode
@dataclass
class TypeDeclaration(ASTNode): name: str; fields: List[TypeField]
@dataclass
class EnumDeclaration(ASTNode): name: str; values: List[Union[str, Tuple[str, ASTNode]]]
@dataclass
class MethodDeclaration(ASTNode): name: str; params: List[Dict[str, Optional[ASTNode]]]; body: List[ASTNode]
@dataclass
class FunctionDeclaration(ASTNode): name: str; params: List[Dict[str, Optional[ASTNode]]]; body: List[ASTNode]
@dataclass
class ImportDeclaration(ASTNode): path: str
@dataclass
class LibraryDeclaration(ASTNode): name: Optional[str] = None
@dataclass
class ExportDeclaration(ASTNode): targets: List[str] = field(default_factory=list)
@dataclass
class Assignment(ASTNode): target: ASTNode; value: ASTNode; operator: str = '='
@dataclass
class IfStatement(ASTNode): condition: ASTNode; then_body: List[ASTNode]; else_body: List[ASTNode]
@dataclass
class ForStatement(ASTNode): iterator: ASTNode; iterable: ASTNode; body: List[ASTNode]
@dataclass
class ForInStatement(ASTNode): targets: List[ASTNode]; iterable: ASTNode; body: List[ASTNode]
@dataclass
class WhileStatement(ASTNode): condition: ASTNode; body: List[ASTNode]
@dataclass
class SwitchStatement(ASTNode): value: Optional[ASTNode]; cases: List[Tuple[ASTNode, List[ASTNode]]]; default_body: List[ASTNode]
@dataclass
class ReturnStatement(ASTNode): value: Optional[ASTNode] = None
@dataclass
class BreakStatement(ASTNode): pass
@dataclass
class ContinueStatement(ASTNode): pass
@dataclass
class ExpressionStatement(ASTNode): expression: ASTNode
@dataclass
class Directive(ASTNode): name: str; value: str

class TokenType:
    KEYWORD = "keyword"
    IDENTIFIER = "identifier"
    NUMBER = "number"
    STRING = "string"
    OPERATOR = "operator"
    DOT = "dot"
    COMMA = "comma"
    BRACKET = "bracket"
    NEWLINE = "newline"
    INDENT = "indent"
    DEDENT = "dedent"
    COMMENT = "comment"
    EOF = "eof"
    UNKNOWN = "unknown"
    DIRECTIVE = "directive"

@dataclass
class Token:
    type: str
    value: str
    line: int
    col: int

class PineTokenizer:
    # (sama persis dengan v4.0.1)
    def __init__(self, code: str):
        if len(code) > MAX_CODE_SIZE:
            raise ValueError(f"Code too large")
        self.code = code
        self.pos = 0
        self.length = len(code)
        self.line = 1
        self.col = 1
        self.sorted_operators = sorted([
            '**', '+=', '-=', '*=', '/=', '%=', '==', '!=', '>=', '<=', '<<',
            '=>', ':=', '+', '-', '*', '/', '%', '=', '!', '>', '<',
            '&', '|', '^', '~', ':', '?'
        ], key=len, reverse=True)
        self.tokens: List[Token] = []
        self.indent_stack = [0]
        self.at_line_start = True
        self._tokenize()
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            self.tokens.append(Token(TokenType.DEDENT, '', self.line, self.col))
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.col))

    def _tokenize(self):
        while self.pos < self.length:
            ch = self.code[self.pos]
            if self.at_line_start:
                indent_len = 0
                while self.pos < self.length and self.code[self.pos] in (' ', '\t'):
                    if self.code[self.pos] == '\t':
                        indent_len += 4
                    else:
                        indent_len += 1
                    self.pos += 1
                if self.pos >= self.length or self.code[self.pos] == '\n':
                    self.at_line_start = False
                    continue
                if indent_len > self.indent_stack[-1]:
                    self.indent_stack.append(indent_len)
                    self.tokens.append(Token(TokenType.INDENT, '', self.line, self.col))
                elif indent_len < self.indent_stack[-1]:
                    while len(self.indent_stack) > 1 and self.indent_stack[-1] > indent_len:
                        self.indent_stack.pop()
                        self.tokens.append(Token(TokenType.DEDENT, '', self.line, self.col))
                    if self.indent_stack[-1] != indent_len:
                        while len(self.indent_stack) > 1 and self.indent_stack[-1] != indent_len:
                            self.indent_stack.pop()
                            self.tokens.append(Token(TokenType.DEDENT, '', self.line, self.col))
                        if self.indent_stack[-1] != indent_len:
                            self.indent_stack = [0]
                            self.tokens.append(Token(TokenType.DEDENT, '', self.line, self.col))
                self.at_line_start = False
                continue

            if ch == ' ' or ch == '\t':
                self.pos += 1
                self.col += 1
                continue
            if ch == '\n':
                self.tokens.append(Token(TokenType.NEWLINE, '\n', self.line, self.col))
                self.pos += 1
                self.line += 1
                self.col = 1
                self.at_line_start = True
                continue
            if ch == '\r':
                self.pos += 1
                continue

            if ch == '/' and self.pos + 1 < self.length and self.code[self.pos + 1] == '/':
                if self.pos + 2 < self.length:
                    lookahead = self.pos + 2
                    while lookahead < self.length and self.code[lookahead] == ' ':
                        lookahead += 1
                    if lookahead < self.length and self.code[lookahead] == '@':
                        start_line, start_col, start_pos = self.line, self.col, self.pos
                        self.pos = lookahead + 1
                        name_start = self.pos
                        while self.pos < self.length and (self.code[self.pos].isalnum() or self.code[self.pos] == '_'):
                            self.pos += 1
                        name = self.code[name_start:self.pos]
                        value = ''
                        if self.pos < self.length and self.code[self.pos] == '=':
                            self.pos += 1
                            while self.pos < self.length and self.code[self.pos] == ' ':
                                self.pos += 1
                            val_start = self.pos
                            while self.pos < self.length and self.code[self.pos] != '\n':
                                self.pos += 1
                            value = self.code[val_start:self.pos].strip()
                        while self.pos < self.length and self.code[self.pos] != '\n':
                            self.pos += 1
                        self.tokens.append(Token(TokenType.DIRECTIVE, f"{name}={value}", start_line, start_col))
                        continue
                start_line, start_col, start_pos = self.line, self.col, self.pos
                while self.pos < self.length and self.code[self.pos] != '\n':
                    self.pos += 1
                self.tokens.append(Token(TokenType.COMMENT, self.code[start_pos:self.pos], start_line, start_col))
                continue

            if ch == '/' and self.pos + 1 < self.length and self.code[self.pos + 1] == '*':
                start_line, start_col, start_pos = self.line, self.col, self.pos
                depth = 1
                self.pos += 2
                self.col += 2
                while self.pos < self.length and depth > 0:
                    if self.code[self.pos] == '/' and self.pos + 1 < self.length and self.code[self.pos + 1] == '*':
                        depth += 1
                        self.pos += 2
                        self.col += 2
                        continue
                    if self.code[self.pos] == '*' and self.pos + 1 < self.length and self.code[self.pos + 1] == '/':
                        depth -= 1
                        self.pos += 2
                        self.col += 2
                        continue
                    if self.code[self.pos] == '\n':
                        self.line += 1
                        self.col = 1
                    else:
                        self.col += 1
                    self.pos += 1
                self.tokens.append(Token(TokenType.COMMENT, self.code[start_pos:self.pos], start_line, start_col))
                continue

            if ch in ('"', "'"):
                start_line, start_col, start_pos = self.line, self.col, self.pos
                quote = ch
                self.pos += 1
                self.col += 1
                while self.pos < self.length:
                    c = self.code[self.pos]
                    if c == '\\':
                        if self.pos + 1 < self.length:
                            self.pos += 2
                            self.col += 2
                        else:
                            raise SyntaxError(f"Unterminated escape at line {self.line}")
                        continue
                    if c == quote:
                        self.pos += 1
                        self.col += 1
                        break
                    if c == '\n':
                        self.line += 1
                        self.col = 1
                    else:
                        self.col += 1
                    self.pos += 1
                else:
                    raise SyntaxError(f"Unterminated string at line {start_line}")
                self.tokens.append(Token(TokenType.STRING, self.code[start_pos:self.pos], start_line, start_col))
                continue

            if ch.isdigit() or (ch == '.' and self.pos + 1 < self.length and self.code[self.pos + 1].isdigit()):
                start, start_col = self.pos, self.col
                has_dot = False
                has_exp = False
                while self.pos < self.length and (self.pos - start) < MAX_NUMBER_LENGTH:
                    c = self.code[self.pos]
                    if c.isdigit():
                        self.pos += 1
                        self.col += 1
                        continue
                    if c == '.' and not has_dot and not has_exp and self.pos + 1 < self.length and self.code[self.pos + 1].isdigit():
                        has_dot = True
                        self.pos += 1
                        self.col += 1
                        continue
                    if c in ('e', 'E') and not has_exp:
                        has_exp = True
                        self.pos += 1
                        self.col += 1
                        if self.pos < self.length and self.code[self.pos] in ('+', '-'):
                            self.pos += 1
                            self.col += 1
                        if not (self.pos < self.length and self.code[self.pos].isdigit()):
                            raise SyntaxError(f"Invalid exponent at line {self.line}")
                        continue
                    break
                number = self.code[start:self.pos]
                if len(number) > MAX_NUMBER_LENGTH:
                    raise SyntaxError(f"Numeric literal too long at line {self.line}")
                self.tokens.append(Token(TokenType.NUMBER, number, self.line, start_col))
                continue

            if ch == '.':
                self.tokens.append(Token(TokenType.DOT, '.', self.line, self.col))
                self.pos += 1
                self.col += 1
                continue
            if ch == ',':
                self.tokens.append(Token(TokenType.COMMA, ',', self.line, self.col))
                self.pos += 1
                self.col += 1
                continue

            if self.pos + 1 < self.length and self.code[self.pos] == '>' and self.code[self.pos + 1] == '>':
                self.tokens.append(Token(TokenType.OPERATOR, '>', self.line, self.col))
                self.pos += 1
                self.col += 1
                self.tokens.append(Token(TokenType.OPERATOR, '>', self.line, self.col))
                self.pos += 1
                self.col += 1
                continue

            op = None
            for o in self.sorted_operators:
                if self.code.startswith(o, self.pos):
                    op = o
                    break
            if op:
                self.tokens.append(Token(TokenType.OPERATOR, op, self.line, self.col))
                self.pos += len(op)
                self.col += len(op)
                continue

            if ch.isalpha() or ch == '_':
                start, start_col = self.pos, self.col
                while self.pos < self.length and (self.code[self.pos].isalnum() or self.code[self.pos] == '_'):
                    self.pos += 1
                    self.col += 1
                ident = self.code[start:self.pos]
                if ident in ('and', 'or', 'not'):
                    self.tokens.append(Token(TokenType.OPERATOR, ident, self.line, start_col))
                elif ident in ('var', 'varip', 'const', 'if', 'else', 'for', 'while', 'switch',
                              'type', 'enum', 'method', 'import', 'return', 'na', 'true', 'false',
                              'in', 'by', 'to', 'step', 'break', 'continue', 'export', 'library',
                              'case', 'default'):
                    self.tokens.append(Token(TokenType.KEYWORD, ident, self.line, start_col))
                else:
                    self.tokens.append(Token(TokenType.IDENTIFIER, ident, self.line, start_col))
                continue

            if ch in ('(', ')', '{', '}', '[', ']'):
                self.tokens.append(Token(TokenType.BRACKET, ch, self.line, self.col))
                self.pos += 1
                self.col += 1
                continue

            self.tokens.append(Token(TokenType.UNKNOWN, ch, self.line, self.col))
            self.pos += 1
            self.col += 1

    def get_tokens(self) -> List[Token]:
        return self.tokens

class PrattParser:
    def __init__(self, tokens: List[Token], recovery: bool = True):
        self.tokens = tokens
        self.pos = 0
        self.recovery = recovery
        self._recovery_mode = False
        self._recovery_depth = 0
        self.generic_depth = 0
        self._depth = 0

    def _peek(self): return self.tokens[self.pos] if self.pos < len(self.tokens) else None
    def _next(self):
        if self.pos < len(self.tokens):
            tok = self.tokens[self.pos]
            self.pos += 1
            return tok
        return None

    def _expect(self, typ, value=None):
        tok = self._next()
        if not tok:
            if self._recovery_mode: return None
            raise SyntaxError(f"Expected {typ} at EOF")
        if tok.type != typ:
            if self._recovery_mode: return None
            raise SyntaxError(f"Expected {typ}, got {tok.type} at line {tok.line}")
        if value is not None and tok.value != value:
            if self._recovery_mode: return None
            raise SyntaxError(f"Expected '{value}', got '{tok.value}' at line {tok.line}")
        return tok

    def _skip_newlines(self):
        while self._peek() and self._peek().type == TokenType.NEWLINE:
            self._next()

    # Hanya COMMENT dan NEWLINE
    def _skip_comments_and_newlines(self):
        while self._peek() and self._peek().type in (TokenType.COMMENT, TokenType.NEWLINE):
            self._next()

    # Untuk tempat yang butuh melewati INDENT/DEDENT juga (akhir statement di module/block)
    def _skip_whitespace(self):
        while self._peek() and self._peek().type in (TokenType.COMMENT, TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
            self._next()

    def _skip_until_sync(self):
        if self._peek() is None: return
        depth = 0
        while self._peek():
            tok = self._peek()
            if tok.type == TokenType.NEWLINE and depth == 0:
                self._next(); break
            if tok.type == TokenType.DEDENT and depth == 0:
                break
            if tok.type == TokenType.BRACKET:
                if tok.value in ('(', '{', '['): depth += 1
                elif tok.value in (')', '}', ']'):
                    depth -= 1
                    if depth < 0: break
            self._next()
        if self._peek() and self._peek().type == TokenType.NEWLINE:
            self._next()

    def _make_span(self, start, end):
        if start and end:
            return SourceSpan(start.line, start.col, end.line, end.col + len(end.value))
        return None

    def _precedence(self, op):
        return {
            'or':10, 'and':20, '==':30, '!=':30, '>':40, '<':40, '>=':40, '<=':40,
            '|':50, '^':60, '&':70, '<<':80, '+':90, '-':90, '*':100, '/':100, '%':100,
            '**':110, '.':120, '[':130, '(':140, '?':150
        }.get(op,0)

    def _is_right_assoc(self, op): return op in ('**',)

    # ─── TYPE PARSER ─────────────────────
    def _parse_type(self):
        tok = self._peek()
        if not tok or tok.type != TokenType.IDENTIFIER: return None
        parts = [tok.value]
        start_tok = tok
        self._next()
        while self._peek() and self._peek().type == TokenType.DOT:
            self._next()
            next_tok = self._expect(TokenType.IDENTIFIER)
            if next_tok: parts.append(next_tok.value)
        base_name = '.'.join(parts)
        base_node = Identifier(parts[-1]) if len(parts)==1 else QualifiedName(parts)
        if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '<':
            save_pos = self.pos
            self._next()
            params = []
            self.generic_depth += 1
            while self._peek():
                tok2 = self._peek()
                if tok2.type == TokenType.OPERATOR and tok2.value == '>':
                    self._next(); break
                param = self._parse_type()
                if param is None:
                    self.generic_depth -= 1; self.pos = save_pos; return None
                params.append(param)
                if self._peek() and self._peek().type == TokenType.COMMA:
                    self._next()
            self.generic_depth -= 1
            node = GenericType(base_name, params)
            end_tok = self.tokens[self.pos-1] if self.pos>0 else start_tok
            if start_tok and end_tok: node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col+len(end_tok.value))
            return node
        node = base_node
        node.span = SourceSpan(start_tok.line, start_tok.col, start_tok.line, start_tok.col+len(start_tok.value))
        return node

    def _try_parse_generic(self, base):
        save_pos = self.pos
        if not (self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '<'): return None
        self._next()
        params = []
        self.generic_depth += 1
        while self._peek():
            tok = self._peek()
            if tok.type == TokenType.OPERATOR and tok.value == '>':
                self._next(); break
            param = self._parse_type()
            if param is None:
                self.generic_depth -= 1; self.pos = save_pos; return None
            params.append(param)
            if self._peek() and self._peek().type == TokenType.COMMA:
                self._next()
        self.generic_depth -= 1
        base_name = base.name if isinstance(base, Identifier) else '.'.join(base.parts)
        node = GenericType(base_name, params)
        start_tok = self.tokens[save_pos] if save_pos<len(self.tokens) else None
        end_tok = self.tokens[self.pos-1] if self.pos>0 else None
        if start_tok and end_tok: node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col+len(end_tok.value))
        return node

    # ─── Expression ──────────────────────
    def parse_expr(self, min_prec=0):
        if self._depth > MAX_PARSE_DEPTH: raise SyntaxError("Maximum parse depth exceeded")
        self._depth += 1
        start_tok = self._peek()
        left = self._parse_prefix()
        if left is None: self._depth -= 1; return None
        if start_tok is None: start_tok = self._peek()
        while True:
            tok = self._peek()
            if not tok or tok.type == TokenType.NEWLINE or tok.type == TokenType.EOF: break
            if tok.type == TokenType.OPERATOR:
                if tok.value == '?' and self._precedence('?') >= min_prec:
                    left = self._parse_ternary(left); continue
                if tok.value == '=': break
                if tok.value == '<' and isinstance(left, (Identifier, QualifiedName)):
                    save_pos = self.pos
                    self._next()
                    next_tok = self._peek()
                    if next_tok and (next_tok.type == TokenType.IDENTIFIER or next_tok.type == TokenType.KEYWORD):
                        self.pos = save_pos
                        generic = self._try_parse_generic(left)
                        if generic: left = generic; continue
                    self.pos = save_pos
                prec = self._precedence(tok.value)
                if prec < min_prec or prec == 0: break
                left = self._parse_infix(left, tok.value, prec)
            elif tok.type == TokenType.DOT:
                left = self._parse_member_access(left)
            elif tok.type == TokenType.BRACKET and tok.value == '[':
                left = self._parse_index(left)
            elif tok.type == TokenType.BRACKET and tok.value == '(':
                left = self._parse_call(left)
            else: break
        if left.span is None:
            end_tok = self.tokens[self.pos-1] if self.pos>0 else start_tok
            left.span = self._make_span(start_tok, end_tok)
        self._depth -= 1
        return left

    def _parse_prefix(self):
        tok = self._next()
        if not tok: return None
        span = SourceSpan(tok.line, tok.col, tok.line, tok.col+len(tok.value))
        if tok.type == TokenType.NUMBER:
            val = tok.value
            node = FloatLiteral(float(val)) if '.' in val or 'e' in val.lower() else IntegerLiteral(int(val))
            node.span = span; return node
        if tok.type == TokenType.STRING:
            raw = tok.value[1:-1]; res = []; i=0
            while i < len(raw):
                if raw[i]=='\\' and i+1<len(raw):
                    c=raw[i+1]
                    if c=='n': res.append('\n')
                    elif c=='t': res.append('\t')
                    elif c=='r': res.append('\r')
                    elif c=='\\': res.append('\\')
                    elif c=='"': res.append('"')
                    elif c=="'": res.append("'")
                    else: res.append(c)
                    i+=2
                else: res.append(raw[i]); i+=1
            node = StringLiteral(''.join(res)); node.span = span; return node
        if tok.type == TokenType.KEYWORD:
            if tok.value == 'true': node = BoolLiteral(True); node.span=span; return node
            if tok.value == 'false': node = BoolLiteral(False); node.span=span; return node
            if tok.value == 'na': node = Identifier('na'); node.span=span; return node
        if tok.type == TokenType.IDENTIFIER:
            parts = [tok.value]; start_line, start_col = tok.line, tok.col
            while self._peek() and self._peek().type == TokenType.DOT:
                self._next(); next_tok = self._expect(TokenType.IDENTIFIER)
                if next_tok: parts.append(next_tok.value)
            if len(parts)>1:
                node = QualifiedName(parts)
                end_tok = next_tok if len(parts)>1 else tok
                node.span = SourceSpan(start_line, start_col, end_tok.line, end_tok.col+len(end_tok.value))
            else:
                node = Identifier(parts[0]); node.span = span
            return node
        if tok.type == TokenType.OPERATOR and tok.value in ('+','-','not','!','~'):
            operand = self.parse_expr(self._precedence(tok.value)+1)
            if operand is None:
                if self._recovery_mode: return None
                raise SyntaxError(f"Expected operand after '{tok.value}'")
            node = UnaryOp(tok.value, operand); node.span = span; return node
        if tok.type == TokenType.BRACKET and tok.value == '(':
            start_pos = self.pos
            params = self._parse_arrow_params_after_open()
            if params is not None and self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '=>':
                self._next(); body = self.parse_expr(0)
                if body is None:
                    if self._recovery_mode: return None
                    raise SyntaxError("Expected body after '=>'")
                node = ArrowFunction(params, body)
                node.span = SourceSpan(tok.line, tok.col, body.span.end_line if body.span else tok.line, body.span.end_col if body.span else tok.col)
                return node
            self.pos = start_pos
            expr = self.parse_expr(0)
            if expr is None:
                if self._recovery_mode: return None
                raise SyntaxError("Expected expression inside parentheses")
            self._expect(TokenType.BRACKET, ')')
            return expr
        if tok.type == TokenType.BRACKET and tok.value == '[':
            elements = []
            while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == ']'):
                self._skip_comments_and_newlines()
                elem = self.parse_expr(0)
                if elem is None: break
                elements.append(elem)
                if self._peek() and self._peek().type == TokenType.COMMA: self._next()
            self._expect(TokenType.BRACKET, ']')
            node = TupleLiteral(elements); node.span = span; return node
        if tok.type == TokenType.UNKNOWN:
            if self._recovery_mode: return None
        self.pos -= 1; return None

    def _parse_arrow_params_after_open(self):
        params = []
        while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == ')'):
            self._skip_comments_and_newlines()
            if not self._peek(): break
            typ = None
            # Cek apakah ada tipe: identifier diikuti identifier atau generic
            if self._peek().type == TokenType.IDENTIFIER:
                typ_tok = self._peek()
                # Cek apakah token berikutnya adalah identifier (berarti typ_tok adalah tipe)
                if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == TokenType.IDENTIFIER:
                    # Ada tipe, ambil tipe
                    self._next()  # konsumsi typ_tok
                    # Cek generic
                    if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '<':
                        typ = self._try_parse_generic(Identifier(typ_tok.value))
                        if typ is None: typ = Identifier(typ_tok.value)
                    else:
                        typ = Identifier(typ_tok.value)
                elif self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == TokenType.OPERATOR and self.tokens[self.pos + 1].value == '<':
                    # Generic type
                    self._next()
                    typ = self._try_parse_generic(Identifier(typ_tok.value))
                    if typ is None: typ = Identifier(typ_tok.value)
                # Jika tidak ada tipe, biarkan typ = None
            name_tok = self._expect(TokenType.IDENTIFIER)
            default = None
            if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '=':
                self._next(); default = self.parse_expr(0)
            if name_tok:
                params.append({'name': name_tok.value, 'type': typ, 'default': default})
            if self._peek() and self._peek().type == TokenType.COMMA:
                self._next()
        if not (self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == ')'):
            return None
        self._next()
        return params

    def _parse_infix(self, left, op, prec):
        self._next()
        right = self.parse_expr(prec+1 if not self._is_right_assoc(op) else prec)
        if right is None:
            if self._recovery_mode: return left
            raise SyntaxError(f"Expected right operand for '{op}'")
        node = BinaryOp(op, left, right)
        if left.span and right.span: node.span = SourceSpan(left.span.start_line, left.span.start_col, right.span.end_line, right.span.end_col)
        elif left.span: node.span = left.span
        return node

    def _parse_ternary(self, condition):
        self._next(); then_expr = self.parse_expr(0)
        if then_expr is None:
            if self._recovery_mode: return condition
            raise SyntaxError("Expected expression after '?'")
        self._expect(TokenType.OPERATOR, ':'); else_expr = self.parse_expr(0)
        if else_expr is None:
            if self._recovery_mode: return condition
            raise SyntaxError("Expected expression after ':'")
        node = TernaryOp(condition, then_expr, else_expr)
        if condition.span and else_expr.span: node.span = SourceSpan(condition.span.start_line, condition.span.start_col, else_expr.span.end_line, else_expr.span.end_col)
        return node

    def _parse_member_access(self, target):
        self._next(); tok = self._expect(TokenType.IDENTIFIER)
        if not tok: return target
        node = MemberAccess(target, tok.value)
        if target.span: node.span = SourceSpan(target.span.start_line, target.span.start_col, tok.line, tok.col+len(tok.value))
        return node

    def _parse_index(self, target):
        self._next(); idx = self.parse_expr(0)
        if idx is None:
            if self._recovery_mode: return target
            raise SyntaxError("Expected expression inside '[]'")
        self._expect(TokenType.BRACKET, ']')
        node = Index(target, idx)
        if target.span: node.span = SourceSpan(target.span.start_line, target.span.start_col, self.tokens[self.pos-1].line, self.tokens[self.pos-1].col+1)
        return node

    def _try_parse_keyword_arg(self):
        """Coba parse keyword argument: identifier = expr.
        Kembalikan Assignment node jika match, None jika bukan keyword arg."""
        saved = self.pos
        tok = self._peek()
        if tok and tok.type == TokenType.IDENTIFIER:
            self._next()
            nxt = self._peek()
            if nxt and nxt.type == TokenType.OPERATOR and nxt.value == '=':
                self._next()
                value = self.parse_expr(0)
                if value is not None:
                    target = Identifier(tok.value)
                    if hasattr(tok, 'line'):
                        target.span = SourceSpan(tok.line, tok.col, tok.line, tok.col + len(tok.value))
                    node = Assignment(target, value)
                    if target.span and value.span:
                        node.span = SourceSpan(target.span.start_line, target.span.start_col, value.span.end_line, value.span.end_col)
                    return node
        self.pos = saved
        return None

    def _parse_call(self, func):
        self._next(); args = []
        while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == ')'):
            self._skip_comments_and_newlines()
            arg = self._try_parse_keyword_arg()
            if arg is None:
                arg = self.parse_expr(0)
            if arg is None: break
            args.append(arg)
            if self._peek() and self._peek().type == TokenType.COMMA: self._next()
        end_tok = self._peek(); self._expect(TokenType.BRACKET, ')')
        node = Call(func, args)
        if func.span and end_tok: node.span = SourceSpan(func.span.start_line, func.span.start_col, end_tok.line, end_tok.col+1)
        elif func.span: node.span = func.span
        return node

    # ─── Statement ───────────────────────
    def parse_statement(self):
        self._skip_comments_and_newlines()
        tok = self._peek()
        if not tok: return None
        if tok.type == TokenType.DIRECTIVE:
            self._next(); parts = tok.value.split('=',1)
            name = parts[0] if parts else ''; value = parts[1] if len(parts)>1 else ''
            node = Directive(name, value); node.span = SourceSpan(tok.line, tok.col, tok.line, tok.col+len(tok.value))
            return node
        if tok.type == TokenType.IDENTIFIER and self._looks_like_function_declaration():
            return self._parse_function_decl()
        if tok.type == TokenType.KEYWORD:
            if tok.value in ('var','varip'): return self._parse_var_decl()
            if tok.value == 'const': return self._parse_const_decl()
            if tok.value == 'type': return self._parse_type_decl()
            if tok.value == 'enum': return self._parse_enum_decl()
            if tok.value == 'method': return self._parse_method_decl()
            if tok.value == 'import': return self._parse_import()
            if tok.value == 'if': return self._parse_if()
            if tok.value == 'for': return self._parse_for()
            if tok.value == 'while': return self._parse_while()
            if tok.value == 'switch': return self._parse_switch()
            if tok.value == 'return': return self._parse_return()
            if tok.value == 'break': self._next(); return BreakStatement()
            if tok.value == 'continue': self._next(); return ContinueStatement()
            if tok.value == 'export': return self._parse_export()
            if tok.value == 'library': return self._parse_library()
        start_tok = self._peek(); old_pos = self.pos
        left_expr = self.parse_expr(0)
        if left_expr is None:
            if self._recovery_mode and self.pos == old_pos: self._next()
            return None
        if isinstance(left_expr, TupleLiteral):
            if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value in ('=', ':='):
                op = self._next(); value = self.parse_expr(0)
                if value is None:
                    if self._recovery_mode: self._skip_until_sync(); return None
                    raise SyntaxError(f"Expected value after '{op.value}'")
                node = DestructuringAssignment(left_expr.elements, value); node.span = left_expr.span
                return node
        tok = self._peek()
        if tok and tok.type == TokenType.OPERATOR and tok.value in ('=',':=','+=','-=','*=','/=','%='):
            self._next(); value = self.parse_expr(0)
            if value is None:
                if self._recovery_mode: self._skip_until_sync(); return None
                raise SyntaxError(f"Expected value after '{tok.value}'")
            node = Assignment(left_expr, value, tok.value)
            if left_expr.span: node.span = left_expr.span
            return node
        node = ExpressionStatement(left_expr); node.span = left_expr.span
        return node

    def _looks_like_function_declaration(self):
        if self.pos+1 >= len(self.tokens): return False
        if self.tokens[self.pos+1].type != TokenType.BRACKET or self.tokens[self.pos+1].value != '(': return False
        depth=0; i=self.pos+1
        while i < len(self.tokens):
            tok = self.tokens[i]
            if tok.type == TokenType.BRACKET:
                if tok.value == '(': depth+=1
                elif tok.value == ')':
                    depth-=1
                    if depth==0:
                        if i+1<len(self.tokens) and self.tokens[i+1].type == TokenType.OPERATOR and self.tokens[i+1].value == '=>': return True
                        return False
            i+=1
        return False

    def _parse_block(self):
        self._skip_comments_and_newlines()
        stmts = []
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '{':
            self._next()
            while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == '}'):
                old_pos = self.pos
                stmt = self.parse_statement()
                if stmt: stmts.append(stmt)
                elif self._recovery_mode and self.pos == old_pos: self._next()
                self._skip_comments_and_newlines()
            self._expect(TokenType.BRACKET, '}')
            return stmts
        if self._peek() and self._peek().type == TokenType.INDENT:
            self._next()
            while self._peek() and self._peek().type not in (TokenType.DEDENT, TokenType.EOF):
                old_pos = self.pos
                stmt = self.parse_statement()
                if stmt: stmts.append(stmt)
                elif self._recovery_mode and self.pos == old_pos: self._next()
                self._skip_comments_and_newlines()
            if self._peek() and self._peek().type == TokenType.DEDENT: self._next()
        else:
            stmt = self.parse_statement()
            if stmt: stmts.append(stmt)
        return stmts

    def _parse_var_decl(self):
        tok = self._expect(TokenType.KEYWORD)
        if tok is None:
            if self._recovery_mode: self._skip_until_sync(); return None
            raise SyntaxError("Expected 'var' or 'varip'")
        varip = tok.value == 'varip'
        typ = None
        if self._peek() and self._peek().type == TokenType.IDENTIFIER:
            first = self._peek()
            if self.pos+1 < len(self.tokens):
                next_tok = self.tokens[self.pos+1]
                if next_tok.type == TokenType.OPERATOR and next_tok.value == '<':
                    self._next(); typ = self._try_parse_generic(Identifier(first.value))
                    if typ is None: typ = Identifier(first.value)
                elif next_tok.type == TokenType.IDENTIFIER:
                    self._next(); typ = Identifier(first.value)
        name_tok = self._expect(TokenType.IDENTIFIER)
        if name_tok is None:
            if self._recovery_mode: self._skip_until_sync(); return None
            raise SyntaxError("Expected variable name")
        value = None
        if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value in ('=', ':='):
            self._next(); value = self.parse_expr(0)
        node = VarDeclaration(varip, typ, name_tok.value, value)
        node.span = SourceSpan(name_tok.line, name_tok.col, name_tok.line, name_tok.col+len(name_tok.value))
        return node

    def _parse_const_decl(self):
        self._expect(TokenType.KEYWORD, 'const')
        name_tok = self._expect(TokenType.IDENTIFIER)
        if name_tok is None:
            if self._recovery_mode: self._skip_until_sync(); return None
            raise SyntaxError("Expected constant name")
        self._expect(TokenType.OPERATOR, '=')
        value = self.parse_expr(0)
        if value is None:
            if self._recovery_mode: value = IntegerLiteral(0)
            else: raise SyntaxError(f"Expected value for const '{name_tok.value}'")
        node = ConstDeclaration(name_tok.value, value)
        node.span = SourceSpan(name_tok.line, name_tok.col, name_tok.line, name_tok.col+len(name_tok.value))
        return node

    def _parse_body_with_indent_or_braces(self, parse_item_fn):
        """Helper untuk parse body dengan { } atau INDENT/DEDENT.
        
        Args:
            parse_item_fn: Function yang parse satu item dan return (name, value) tuple
                          atau None jika gagal
        
        Returns:
            List of (name, value) tuples
        """
        items = []
        
        # Bracket mode: { ... }
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '{':
            self._next()  # consume {
            while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == '}'):
                self._skip_comments_and_newlines()
                result = parse_item_fn()
                if result is None:
                    if self._recovery_mode:
                        self._skip_until_sync()
                        break
                    raise SyntaxError("Failed to parse item in bracket block")
                items.append(result)
                if self._peek() and self._peek().type == TokenType.COMMA:
                    self._next()
            self._expect(TokenType.BRACKET, '}')
        
        # Indent mode
        else:
            self._skip_comments_and_newlines()
            if self._peek() and self._peek().type == TokenType.INDENT:
                self._next()  # consume INDENT
                while self._peek() and self._peek().type not in (TokenType.DEDENT, TokenType.EOF):
                    self._skip_comments_and_newlines()
                    result = parse_item_fn()
                    if result is None:
                        break
                    items.append(result)
                if self._peek() and self._peek().type == TokenType.DEDENT:
                    self._next()  # consume DEDENT
        
        return items

    def _parse_type_decl(self):
        start_tok = self._peek()
        self._expect(TokenType.KEYWORD, 'type')
        name_tok = self._expect(TokenType.IDENTIFIER)
        if name_tok is None:
            if self._recovery_mode: self._skip_until_sync(); return None
            raise SyntaxError("Expected type name")
        fields = []
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '{':
            self._next()
            while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == '}'):
                self._skip_comments_and_newlines()
                field_type = None
                if self._peek() and self._peek().type == TokenType.IDENTIFIER:
                    typ_tok = self._next()
                    if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '<':
                        field_type = self._try_parse_generic(Identifier(typ_tok.value))
                        if field_type is None: field_type = Identifier(typ_tok.value)
                    else: field_type = Identifier(typ_tok.value)
                field_name = self._expect(TokenType.IDENTIFIER)
                if field_name is None:
                    if self._recovery_mode:
                        self._skip_until_sync()
                        break
                    raise SyntaxError("Expected field name")
                default = None
                if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '=':
                    self._next(); default = self.parse_expr(0)
                if field_type: fields.append(TypeField(field_name.value, field_type, default))
                if self._peek() and self._peek().type == TokenType.COMMA: self._next()
            self._expect(TokenType.BRACKET, '}')
        else:
            self._skip_comments_and_newlines()  # hanya NEWLINE/COMMENT, INDENT tetap ada
            if self._peek() and self._peek().type == TokenType.INDENT:
                self._next()
            while self._peek() and self._peek().type not in (TokenType.DEDENT, TokenType.EOF):
                self._skip_comments_and_newlines()
                field_type = None
                if self._peek() and self._peek().type == TokenType.IDENTIFIER:
                    typ_tok = self._next()
                    if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '<':
                        field_type = self._try_parse_generic(Identifier(typ_tok.value))
                        if field_type is None: field_type = Identifier(typ_tok.value)
                    else: field_type = Identifier(typ_tok.value)
                field_name = self._expect(TokenType.IDENTIFIER)
                if field_name is None:
                    if self._recovery_mode:
                        self._skip_until_sync()
                        break
                    raise SyntaxError("Expected field name")
                default = None
                if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '=':
                    self._next(); default = self.parse_expr(0)
                if field_type: fields.append(TypeField(field_name.value, field_type, default))
            if self._peek() and self._peek().type == TokenType.DEDENT: self._next()
        node = TypeDeclaration(name_tok.value, fields)
        end_tok = self.tokens[self.pos-1] if self.pos>0 else start_tok
        if start_tok and end_tok: node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col+1)
        return node

    def _parse_enum_decl(self):
        start_tok = self._peek()
        self._expect(TokenType.KEYWORD, 'enum')
        name_tok = self._expect(TokenType.IDENTIFIER)
        if name_tok is None:
            if self._recovery_mode: self._skip_until_sync(); return None
            raise SyntaxError("Expected enum name")
        values = []
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '{':
            self._next()
            while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == '}'):
                self._skip_comments_and_newlines()
                val_tok = self._expect(TokenType.IDENTIFIER)
                if val_tok is None:
                    if self._recovery_mode:
                        self._skip_until_sync()
                        break
                    raise SyntaxError("Expected enum value name")
                title = None
                if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '=':
                    self._next(); title = self.parse_expr(0)
                if title: values.append((val_tok.value, title))
                else: values.append(val_tok.value)
                if self._peek() and self._peek().type == TokenType.COMMA: self._next()
            self._expect(TokenType.BRACKET, '}')
        else:
            self._skip_comments_and_newlines()  # hanya NEWLINE/COMMENT
            if self._peek() and self._peek().type == TokenType.INDENT:
                self._next()
            while self._peek() and self._peek().type not in (TokenType.DEDENT, TokenType.EOF):
                val_tok = self._expect(TokenType.IDENTIFIER)
                if val_tok is None:
                    if self._recovery_mode:
                        self._skip_until_sync()
                        break
                    raise SyntaxError("Expected enum value name")
                title = None
                if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '=':
                    self._next(); title = self.parse_expr(0)
                if title: values.append((val_tok.value, title))
                else: values.append(val_tok.value)
                if self._peek() and self._peek().type == TokenType.COMMA: self._next()
                self._skip_comments_and_newlines()
            if self._peek() and self._peek().type == TokenType.DEDENT: self._next()
        node = EnumDeclaration(name_tok.value, values)
        end_tok = self.tokens[self.pos-1] if self.pos>0 else start_tok
        if start_tok and end_tok: node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col+1)
        return node

    def _parse_params(self):
        self._expect(TokenType.BRACKET, '(')
        params = []
        while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == ')'):
            self._skip_comments_and_newlines()
            if not self._peek(): break
            typ = None
            if self._peek().type == TokenType.IDENTIFIER:
                typ_tok = self._peek()
                if self.pos+1 < len(self.tokens) and self.tokens[self.pos+1].type == TokenType.OPERATOR and self.tokens[self.pos+1].value == '<':
                    self._next(); typ = self._try_parse_generic(Identifier(typ_tok.value))
                    if typ is None: typ = Identifier(typ_tok.value)
                elif self.pos+1 < len(self.tokens) and self.tokens[self.pos+1].type == TokenType.IDENTIFIER:
                    self._next(); typ = Identifier(typ_tok.value)
            name_tok = self._expect(TokenType.IDENTIFIER)
            if name_tok is None:
                if self._recovery_mode:
                    self._skip_until_sync()
                    return params  # return partial params
                raise SyntaxError("Expected parameter name")
            default = None
            if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '=':
                self._next(); default = self.parse_expr(0)
            params.append({'name':name_tok.value, 'type':typ, 'default':default})
            if self._peek() and self._peek().type == TokenType.COMMA: self._next()
        self._expect(TokenType.BRACKET, ')')
        return params

    def _parse_method_decl(self):
        start_tok = self._peek()
        self._expect(TokenType.KEYWORD, 'method')
        name_tok = self._expect(TokenType.IDENTIFIER)
        if name_tok is None:
            if self._recovery_mode: self._skip_until_sync(); return None
            raise SyntaxError("Expected method name")
        params = self._parse_params()
        self._expect(TokenType.OPERATOR, '=>')
        body = []
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '{':
            body = self._parse_block()
        else:
            if self._peek() and self._peek().type == TokenType.INDENT: body = self._parse_block()
            else:
                expr = self.parse_expr(0)
                if expr: body = [expr]
        node = MethodDeclaration(name_tok.value, params, body)
        end_tok = self.tokens[self.pos-1] if self.pos>0 else start_tok
        if start_tok and end_tok: node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col+1)
        return node

    def _parse_function_decl(self):
        start_tok = self._peek()
        name_tok = self._expect(TokenType.IDENTIFIER)
        if name_tok is None:
            if self._recovery_mode: self._skip_until_sync(); return None
            raise SyntaxError("Expected function name")
        params = self._parse_params()
        if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '=>': self._next()
        else:
            if self._recovery_mode: pass
            else: raise SyntaxError("Expected '=>' after function parameters")
        body = []
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '{': body = self._parse_block()
        else:
            if self._peek() and self._peek().type == TokenType.INDENT: body = self._parse_block()
            else:
                expr = self.parse_expr(0)
                if expr: body = [expr]
        node = FunctionDeclaration(name_tok.value, params, body)
        end_tok = self.tokens[self.pos-1] if self.pos>0 else start_tok
        if start_tok and end_tok: node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col+1)
        return node

    def _parse_import(self):
        self._expect(TokenType.KEYWORD, 'import'); start_tok = self._peek()
        path_tokens = []
        while self._peek() and self._peek().type not in (TokenType.NEWLINE, TokenType.COMMENT, TokenType.EOF):
            path_tokens.append(self._next())
        path = ' '.join(t.value for t in path_tokens if t)
        path = re.sub(r'\s*/\s*', '/', path)
        node = ImportDeclaration(path)
        end_tok = self.tokens[self.pos-1] if self.pos>0 else start_tok
        if start_tok and end_tok: node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col+1)
        return node

    def _parse_export(self):
        self._expect(TokenType.KEYWORD, 'export'); targets = []
        while self._peek() and self._peek().type not in (TokenType.NEWLINE, TokenType.EOF):
            tok = self._next()
            if tok and tok.type == TokenType.IDENTIFIER: targets.append(tok.value)
        return ExportDeclaration(targets)

    def _parse_library(self):
        self._expect(TokenType.KEYWORD, 'library'); name = None
        if self._peek() and self._peek().type == TokenType.IDENTIFIER: name = self._next().value
        while self._peek() and self._peek().type not in (TokenType.NEWLINE, TokenType.EOF): self._next()
        return LibraryDeclaration(name)

    def _parse_if(self):
        self._expect(TokenType.KEYWORD, 'if'); start_tok = self._peek()
        condition = self.parse_expr(0)
        if condition is None:
            if self._recovery_mode: self._skip_until_sync(); return None
            raise SyntaxError("Expected condition after 'if'")
        then_body = self._parse_block()
        else_body = []
        self._skip_comments_and_newlines()
        if self._peek() and self._peek().type == TokenType.KEYWORD and self._peek().value == 'else':
            self._next(); self._skip_comments_and_newlines()
            if self._peek() and self._peek().type == TokenType.KEYWORD and self._peek().value == 'if':
                nested = self._parse_if()
                if nested: else_body = [nested]
            else: else_body = self._parse_block()
        node = IfStatement(condition, then_body, else_body)
        end_tok = self.tokens[self.pos-1] if self.pos>0 else start_tok
        if start_tok and end_tok: node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col+1)
        return node

    def _parse_for(self):
        self._expect(TokenType.KEYWORD, 'for'); start_tok = self._peek()
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '[':
            targets = []; self._next()
            while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == ']'):
                self._skip_comments_and_newlines(); target = self.parse_expr(0)
                if target is None: break
                targets.append(target)
                if self._peek() and self._peek().type == TokenType.COMMA: self._next()
            self._expect(TokenType.BRACKET, ']'); self._expect(TokenType.KEYWORD, 'in')
            iterable = self.parse_expr(0)
            if iterable is None:
                if self._recovery_mode: self._skip_until_sync(); return None
                raise SyntaxError("Expected iterable after 'in'")
            body = self._parse_block()
            node = ForInStatement(targets, iterable, body)
            if start_tok: node.span = self._make_span(start_tok, self.tokens[self.pos-1] if self.pos>0 else start_tok)
            return node
        iterator_tok = self._expect(TokenType.IDENTIFIER)
        if not iterator_tok:
            if self._recovery_mode: self._skip_until_sync(); return None
            raise SyntaxError("Expected iterator name after 'for'")
        if self._peek() and self._peek().type == TokenType.KEYWORD and self._peek().value == 'in':
            self._next(); iterable = self.parse_expr(0)
            if iterable is None:
                if self._recovery_mode: self._skip_until_sync(); return None
                raise SyntaxError("Expected iterable after 'in'")
            body = self._parse_block()
            node = ForStatement(Identifier(iterator_tok.value), iterable, body)
            if iterator_tok: node.span = SourceSpan(iterator_tok.line, iterator_tok.col, iterator_tok.line, iterator_tok.col+len(iterator_tok.value))
            return node
        self._expect(TokenType.OPERATOR, '='); start = self.parse_expr(0)
        if start is None:
            if self._recovery_mode: self._skip_until_sync(); return None
            raise SyntaxError("Expected start value after '='")
        if not (self._peek() and self._peek().type == TokenType.KEYWORD and self._peek().value == 'to'):
            if self._recovery_mode: self._skip_until_sync(); return None
            raise SyntaxError("Expected 'to' after start value")
        self._next(); end = self.parse_expr(0)
        if end is None:
            if self._recovery_mode: end = IntegerLiteral(0)
            else: raise SyntaxError("Expected end value after 'to'")
        step = None
        if self._peek() and self._peek().type == TokenType.KEYWORD and self._peek().value == 'by':
            self._next(); step = self.parse_expr(0)
        iterable = RangeExpr(start, end, step)
        if start_tok: iterable.span = self._make_span(start_tok, self.tokens[self.pos-1] if self.pos>0 else start_tok)
        body = self._parse_block()
        node = ForStatement(Identifier(iterator_tok.value), iterable, body)
        if iterator_tok: node.span = SourceSpan(iterator_tok.line, iterator_tok.col, iterator_tok.line, iterator_tok.col+len(iterator_tok.value))
        return node

    def _parse_while(self):
        self._expect(TokenType.KEYWORD, 'while'); start_tok = self._peek()
        condition = self.parse_expr(0)
        if condition is None:
            if self._recovery_mode: self._skip_until_sync(); return None
            raise SyntaxError("Expected condition after 'while'")
        body = self._parse_block()
        node = WhileStatement(condition, body)
        end_tok = self.tokens[self.pos-1] if self.pos>0 else start_tok
        if start_tok and end_tok: node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col+1)
        return node

    def _parse_switch(self):
        self._expect(TokenType.KEYWORD, 'switch'); start_tok = self._peek()
        value = None
        tok = self._peek()
        if tok and tok.type not in (TokenType.NEWLINE, TokenType.INDENT, TokenType.BRACKET, TokenType.COMMENT, TokenType.EOF):
            if not (tok.type == TokenType.OPERATOR and tok.value == '=>'): value = self.parse_expr(0)
        cases = []; default_body = []
        self._skip_comments_and_newlines()
        def parse_cases_block():
            nonlocal default_body
            while self._peek() and not ((self._peek().type == TokenType.BRACKET and self._peek().value == '}') or self._peek().type in (TokenType.DEDENT, TokenType.EOF)):
                self._skip_comments_and_newlines()
                if not self._peek(): break
                if self._peek().type == TokenType.KEYWORD and self._peek().value == 'default':
                    self._next()
                    if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '=>': self._next()
                    default_body = self._parse_block(); break
                if self._peek().type == TokenType.KEYWORD and self._peek().value == 'case': self._next()
                case_value = self.parse_expr(0)
                if case_value is None:
                    if self._recovery_mode:
                        self._skip_until_sync()
                        continue
                    raise SyntaxError("Expected case value")
                if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '=>': self._next()
                else:
                    if self._recovery_mode: self._skip_until_sync(); continue
                    raise SyntaxError("Expected '=>' after case value")
                body = self._parse_block(); cases.append((case_value, body))
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '{':
            self._next(); parse_cases_block(); self._expect(TokenType.BRACKET, '}')
        else:
            if self._peek() and self._peek().type == TokenType.INDENT: self._next()
            parse_cases_block()
            if self._peek() and self._peek().type == TokenType.DEDENT: self._next()
        node = SwitchStatement(value, cases, default_body)
        end_tok = self.tokens[self.pos-1] if self.pos>0 else start_tok
        if start_tok and end_tok: node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col+1)
        return node

    def _parse_return(self):
        self._expect(TokenType.KEYWORD, 'return'); start_tok = self._peek()
        value = None if (self._peek() and self._peek().type == TokenType.NEWLINE) else self.parse_expr(0)
        node = ReturnStatement(value)
        if start_tok:
            end_tok = self.tokens[self.pos-1] if self.pos>0 else start_tok
            node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col+1)
        return node

class PineAST:
    def __init__(self, code):
        self.code = code
        self.symbols = {}
        self.arrays = []
        self.matrices = []
        self.constants = {}
        self.functions = []
        self.types = []
        self.enums = []
        self.methods = []
        self.imports = []
        self.directives = []
        self.tokens = PineTokenizer(code).get_tokens()
        self.parser = PrattParser(self.tokens, recovery=True)
        self.root = self._parse_module()
        self._extract_symbols(self.root)
        self._extract_symbols_fallback()

    def _parse_module(self):
        body = []
        while self.parser._peek() and self.parser._peek().type != TokenType.EOF:
            old_pos = self.parser.pos
            try:
                self.parser._recovery_mode = True
                self.parser._recovery_depth += 1
                stmt = self.parser.parse_statement()
                self.parser._recovery_depth -= 1
                self.parser._recovery_mode = False if self.parser._recovery_depth == 0 else True
                if stmt: body.append(stmt)
                elif self.parser.pos == old_pos: self.parser._next()
            except SyntaxError:
                self.parser._recovery_mode = True
                self.parser._skip_until_sync()
                self.parser._recovery_mode = False
            self.parser._skip_whitespace()  # gunakan _skip_whitespace setelah statement
        return Module(body)

    def _extract_symbols(self, node):
        if isinstance(node, Module):
            for stmt in node.body: self._extract_symbols(stmt)
            return
        if isinstance(node, VarDeclaration):
            name = node.name
            if name:
                if node.type and isinstance(node.type, GenericType):
                    base = node.type.base
                    if base == 'array': self.symbols[name] = 'array'; self.arrays.append(name)
                    elif base == 'matrix': self.symbols[name] = 'matrix'; self.matrices.append(name)
                    else: self.symbols[name] = 'var'
                elif node.value and isinstance(node.value, Call):
                    func = node.value.func
                    if isinstance(func, QualifiedName) and func.parts and func.parts[0] == 'array':
                        self.symbols[name] = 'array'; self.arrays.append(name)
                    elif isinstance(func, QualifiedName) and func.parts and func.parts[0] == 'matrix':
                        self.symbols[name] = 'matrix'; self.matrices.append(name)
                    else: self.symbols[name] = 'var'
                else: self.symbols[name] = 'var'
            if node.value: self._extract_symbols(node.value)
            if node.type: self._extract_symbols(node.type)
        elif isinstance(node, ConstDeclaration):
            name = node.name
            if isinstance(node.value, IntegerLiteral): self.constants[name] = node.value.value
            elif isinstance(node.value, FloatLiteral): self.constants[name] = node.value.value
            self.symbols[name] = 'const'
            self._extract_symbols(node.value)
        elif isinstance(node, FunctionDeclaration):
            self.functions.append(node.name); self.symbols[node.name] = 'function'
            for p in node.params:
                if p.get('type'): self._extract_symbols(p['type'])
                if p.get('default'): self._extract_symbols(p['default'])
            for stmt in node.body: self._extract_symbols(stmt)
        elif isinstance(node, MethodDeclaration):
            self.methods.append({'name':node.name, 'params':node.params}); self.symbols[node.name] = 'method'
            for p in node.params:
                if p.get('type'): self._extract_symbols(p['type'])
                if p.get('default'): self._extract_symbols(p['default'])
            for stmt in node.body: self._extract_symbols(stmt)
        elif isinstance(node, TypeDeclaration):
            self.types.append({'name':node.name, 'fields':node.fields}); self.symbols[node.name] = 'type'
            for f in node.fields:
                if f.type: self._extract_symbols(f.type)
                if f.default: self._extract_symbols(f.default)
        elif isinstance(node, EnumDeclaration):
            self.enums.append({'name':node.name, 'values':node.values}); self.symbols[node.name] = 'enum'
            for v in node.values:
                if isinstance(v, tuple) and len(v)==2: self._extract_symbols(v[1])
        elif isinstance(node, ImportDeclaration): self.imports.append(node.path); self.symbols[f"import_{node.path}"] = 'import'
        elif isinstance(node, Directive): self.directives.append({'name':node.name, 'value':node.value})
        elif isinstance(node, Assignment):
            if isinstance(node.target, Identifier): self.symbols[node.target.name] = self.symbols.get(node.target.name, 'var')
            self._extract_symbols(node.target); self._extract_symbols(node.value)
        elif isinstance(node, DestructuringAssignment):
            for t in node.targets: self._extract_symbols(t)
            self._extract_symbols(node.value)
        elif isinstance(node, IfStatement):
            self._extract_symbols(node.condition)
            for s in node.then_body: self._extract_symbols(s)
            for s in node.else_body: self._extract_symbols(s)
        elif isinstance(node, ForStatement):
            self._extract_symbols(node.iterator); self._extract_symbols(node.iterable)
            for s in node.body: self._extract_symbols(s)
        elif isinstance(node, ForInStatement):
            for t in node.targets: self._extract_symbols(t)
            self._extract_symbols(node.iterable)
            for s in node.body: self._extract_symbols(s)
        elif isinstance(node, WhileStatement):
            self._extract_symbols(node.condition)
            for s in node.body: self._extract_symbols(s)
        elif isinstance(node, SwitchStatement):
            if node.value: self._extract_symbols(node.value)
            for _, body in node.cases:
                for s in body: self._extract_symbols(s)
            for s in node.default_body: self._extract_symbols(s)
        elif isinstance(node, ExpressionStatement): self._extract_symbols(node.expression)
        elif isinstance(node, ReturnStatement):
            if node.value: self._extract_symbols(node.value)
        elif isinstance(node, BinaryOp): self._extract_symbols(node.left); self._extract_symbols(node.right)
        elif isinstance(node, UnaryOp): self._extract_symbols(node.operand)
        elif isinstance(node, TernaryOp): self._extract_symbols(node.condition); self._extract_symbols(node.then_expr); self._extract_symbols(node.else_expr)
        elif isinstance(node, Call):
            self._extract_symbols(node.func)
            for a in node.args: self._extract_symbols(a)
        elif isinstance(node, Index): self._extract_symbols(node.target); self._extract_symbols(node.index)
        elif isinstance(node, MemberAccess): self._extract_symbols(node.target)
        elif isinstance(node, TupleLiteral):
            for e in node.elements: self._extract_symbols(e)
        elif isinstance(node, ArrowFunction):
            for p in node.params:
                if p.get('type'): self._extract_symbols(p['type'])
                if p.get('default'): self._extract_symbols(p['default'])
            self._extract_symbols(node.body)
        elif isinstance(node, GenericType):
            for p in node.params: self._extract_symbols(p)
        elif isinstance(node, RangeExpr):
            self._extract_symbols(node.start); self._extract_symbols(node.end)
            if node.step: self._extract_symbols(node.step)

    def _extract_symbols_fallback(self):
        import re
        for m in re.finditer(r'(?:var|varip)\s+(?:(array|matrix)(?:<[^>]+>)?\s+)?(\w+)\s*=\s*(array|matrix)\.new', self.code):
            kind_hint, name, kind = m.group(1), m.group(2), m.group(3)
            if not kind:
                kind = kind_hint  # fallback ke type annotation jika ada
            if kind == 'array' and name not in self.arrays:
                self.arrays.append(name)
                self.symbols[name] = 'array'
            elif kind == 'matrix' and name not in self.matrices:
                self.matrices.append(name)
                self.symbols[name] = 'matrix'
    def get_symbols(self): return self.symbols
    def get_arrays(self): return self.arrays.copy()
    def get_matrices(self): return self.matrices.copy()
    def get_constants(self): return dict(self.constants)
    def get_functions(self): return self.functions
    def get_types(self): return self.types
    def get_enums(self): return self.enums
    def get_methods(self): return self.methods
    def get_imports(self): return self.imports
    def get_directives(self): return self.directives
    def get_root(self): return self.root

if __name__ == "__main__":
    code = """
//@version=6
indicator("Test")
type Features
    float value
    float slope
enum Status
    NAIK
    TURUN = "Turun Title"
method sum(Weights w) => w.value + w.slope
var int counter = 0
var array<float> prices
const MAX = 100
f_test() => true
ta.ema(close, 14)
if close > open
    plot(close)
else if close < open
    plot(open)
else
    plot(hl2)
for i = 1 to 10 by 2
    x := x + i
switch x
    case 1 => foo()
    case 2 => bar()
    default => default()
"""
    ast = PineAST(code)
    print(f"Symbols: {ast.get_symbols()}")
    print(f"Types: {ast.get_types()}")
    print(f"Enums: {ast.get_enums()}")
    print(f"Methods: {ast.get_methods()}")
    print(f"Constants: {ast.get_constants()}")
    print(f"Functions: {ast.get_functions()}")
    print(f"Imports: {ast.get_imports()}")
    print(f"Directives: {ast.get_directives()}")
    print(f"Root body types: {[type(n).__name__ for n in ast.root.body]}")
