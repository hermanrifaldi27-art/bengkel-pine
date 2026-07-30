#!/usr/bin/env python3
"""
PineAST v3.4 — Pratt Parser untuk Pine Script v6
Fix: span accuracy, body multiline indent, switch variants, for-in, generic type,
     array/matrix detection, constants typing, tuple literal vs pattern,
     QualifiedName consistency, all span, recovery, grammar completeness
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Union, Tuple

# ─── CONSTANTS ──────────────────────────────────────────────────────
MAX_CODE_SIZE = 10 * 1024 * 1024
MAX_NUMBER_LENGTH = 50

# ─── SOURCE SPAN ──────────────────────────────────────────────────
@dataclass
class SourceSpan:
    start_line: int
    start_col: int
    end_line: int
    end_col: int

class ASTNode:
    span: Optional[SourceSpan] = None

# ─── AST NODES ──────────────────────────────────────────────────
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
class TuplePattern(ASTNode): elements: List[ASTNode]  # destructuring target
@dataclass
class DestructuringAssignment(ASTNode): targets: List[ASTNode]; value: ASTNode
@dataclass
class GenericType(ASTNode): base: str; params: List[ASTNode]  # array<float>

@dataclass
class VarDeclaration(ASTNode): varip: bool; type: Optional[ASTNode]; name: str; value: Optional[ASTNode]
@dataclass
class ConstDeclaration(ASTNode): name: str; value: ASTNode
@dataclass
class TypeDeclaration(ASTNode): name: str; fields: List[Tuple[str, str]]
@dataclass
class EnumDeclaration(ASTNode): name: str; values: List[str]
@dataclass
class MethodDeclaration(ASTNode): name: str; params: List[Dict[str, Optional[ASTNode]]]; body: Optional[ASTNode]
@dataclass
class FunctionDeclaration(ASTNode): name: str; params: List[Dict[str, Optional[ASTNode]]]; body: Optional[ASTNode]
@dataclass
class ImportDeclaration(ASTNode): path: str
@dataclass
class Assignment(ASTNode): target: ASTNode; value: ASTNode; operator: str = '='
@dataclass
class IfStatement(ASTNode): condition: ASTNode; then_body: List[ASTNode]; else_body: List[ASTNode] = field(default_factory=list)
@dataclass
class ForStatement(ASTNode): iterator: Identifier; iterable: ASTNode; body: List[ASTNode]
@dataclass
class WhileStatement(ASTNode): condition: ASTNode; body: List[ASTNode]
@dataclass
class SwitchStatement(ASTNode): value: ASTNode; cases: List[Tuple[Optional[ASTNode], List[ASTNode]]]; default_body: List[ASTNode] = field(default_factory=list)
@dataclass
class ReturnStatement(ASTNode): value: Optional[ASTNode] = None
@dataclass
class ExpressionStatement(ASTNode): expression: ASTNode
@dataclass
class Directive(ASTNode): name: str; value: str  # //@version=6

# ─── TOKEN TYPES ──────────────────────────────────────────────────
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
    DIRECTIVE = "directive"  # //@version

@dataclass
class Token:
    type: str
    value: str
    line: int
    col: int

# ─── TOKENIZER ────────────────────────────────────────────────────
class PineTokenizer:
    def __init__(self, code: str):
        if len(code) > MAX_CODE_SIZE:
            raise ValueError(f"Code too large: {len(code)} bytes")
        self.code = code
        self.pos = 0
        self.length = len(code)
        self.line = 1
        self.col = 1
        self.sorted_operators = sorted([
            '**', '+=', '-=', '*=', '/=', '%=', '==', '!=', '>=', '<=', '<<', '>>',
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
                        import warnings
                        warnings.warn(f"Inconsistent indentation at line {self.line}")
                        self.indent_stack = [0]
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

            # Directive: //@...
            if ch == '/' and self.pos + 1 < self.length and self.code[self.pos + 1] == '/':
                if self.pos + 2 < self.length and self.code[self.pos + 2] == '@':
                    start_line, start_col, start_pos = self.line, self.col, self.pos
                    self.pos += 3
                    while self.pos < self.length and self.code[self.pos] != '\n':
                        self.pos += 1
                    self.tokens.append(Token(TokenType.DIRECTIVE, self.code[start_pos:self.pos], start_line, start_col))
                    continue
                # normal single-line comment
                start_line, start_col, start_pos = self.line, self.col, self.pos
                while self.pos < self.length and self.code[self.pos] != '\n':
                    self.pos += 1
                self.tokens.append(Token(TokenType.COMMENT, self.code[start_pos:self.pos], start_line, start_col))
                continue

            # Multi-line comment (nested)
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

            # String
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

            # Number
            if ch.isdigit() or (ch == '.' and self.pos + 1 < self.length and self.code[self.pos + 1].isdigit()):
                start, start_col = self.pos, self.col
                has_dot = has_exp = False
                while self.pos < self.length and (self.pos - start) < MAX_NUMBER_LENGTH:
                    c = self.code[self.pos]
                    if c.isdigit():
                        self.pos += 1
                        self.col += 1
                        continue
                    if c == '.' and not has_dot and not has_exp:
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
                    raise SyntaxError(f"Numeric literal exceeds {MAX_NUMBER_LENGTH} digits")
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

            # Operator
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

            # Identifier
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
                              'in', 'by', 'to', 'step', 'break', 'continue', 'case', 'default'):
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

# ─── PARSER ──────────────────────────────────────────────────────
class PrattParser:
    def __init__(self, tokens: List[Token], recovery: bool = True):
        self.tokens = tokens
        self.pos = 0
        self.recovery = recovery
        self._recovery_mode = False

    def _peek(self) -> Optional[Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _next(self) -> Optional[Token]:
        if self.pos < len(self.tokens):
            tok = self.tokens[self.pos]
            self.pos += 1
            return tok
        return None

    def _expect(self, typ: str, value: Optional[str] = None) -> Optional[Token]:
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
    def _skip_comments_and_newlines(self):
        while self._peek() and self._peek().type in (TokenType.COMMENT, TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT):
            self._next()
    def _skip_until_sync(self):
        """Recovery: skip sampai newline, dedent, atau brace balance"""
        depth = 0
        while self._peek():
            tok = self._peek()
            if tok.type == TokenType.NEWLINE and depth == 0:
                self._next()
                break
            if tok.type == TokenType.DEDENT and depth == 0:
                break
            if tok.type == TokenType.BRACKET:
                if tok.value in ('(', '{', '['):
                    depth += 1
                elif tok.value in (')', '}', ']'):
                    depth -= 1
                    if depth < 0:
                        break
            self._next()
        if self._peek() and self._peek().type == TokenType.NEWLINE:
            self._next()

    def _precedence(self, op: str) -> int:
        return {
            'or': 10,
            'and': 20,
            '==': 30, '!=': 30,
            '>': 40, '<': 40, '>=': 40, '<=': 40,
            '|': 50,
            '^': 60,
            '&': 70,
            '<<': 80, '>>': 80,
            '+': 90, '-': 90,
            '*': 100, '/': 100, '%': 100,
            '**': 110,
            '.': 120,
            '[': 130,
            '(': 140,
            '?': 150,
        }.get(op, 0)

    def _is_right_assoc(self, op: str) -> bool:
        return op in ('**',)

    def _make_span(self, start: Optional[Token], end: Optional[Token]) -> SourceSpan:
        if start and end:
            return SourceSpan(start.line, start.col, end.line, end.col + len(end.value))
        return SourceSpan(1, 1, 1, 1)

    # ─── Expression ──────────────────────────────────────────────
    def parse_expr(self, min_prec: int = 0) -> Optional[ASTNode]:
        start_tok = self._peek()
        left = self._parse_prefix()
        if left is None:
            return None
        # get start from token before prefix
        if start_tok is None:
            start_tok = self._peek()
        while True:
            tok = self._peek()
            if not tok or tok.type == TokenType.NEWLINE or tok.type == TokenType.EOF:
                break
            if tok.type == TokenType.OPERATOR:
                if tok.value == '?':
                    left = self._parse_ternary(left)
                    continue
                if tok.value == '=':
                    break
                prec = self._precedence(tok.value)
                if prec < min_prec or prec == 0:
                    break
                left = self._parse_infix(left, tok.value, prec)
            elif tok.type == TokenType.DOT:
                left = self._parse_member_access(left)
            elif tok.type == TokenType.BRACKET and tok.value == '[':
                left = self._parse_index(left)
            elif tok.type == TokenType.BRACKET and tok.value == '(':
                left = self._parse_call(left)
            elif tok.type == TokenType.OPERATOR and tok.value == '<':
                # Generic type: array<float>
                left = self._parse_generic_type(left)
            else:
                break
        # ensure span
        if left and left.span is None:
            end_tok = self.tokens[self.pos-1] if self.pos > 0 else None
            left.span = self._make_span(start_tok, end_tok)
        return left

    def _parse_prefix(self) -> Optional[ASTNode]:
        tok = self._next()
        if not tok:
            return None
        span = SourceSpan(tok.line, tok.col, tok.line, tok.col + len(tok.value))

        if tok.type == TokenType.NUMBER:
            val = tok.value
            node = FloatLiteral(float(val)) if ('.' in val or 'e' in val.lower()) else IntegerLiteral(int(val))
            node.span = span; return node
        if tok.type == TokenType.STRING:
            raw = tok.value[1:-1]
            i, res = 0, []
            while i < len(raw):
                if raw[i] == '\\' and i+1 < len(raw):
                    c = raw[i+1]; pairs = {'n':'\n','t':'\t','r':'\r','\\':'\\','"':'"',"'":"'"}
                    res.append(pairs.get(c, c)); i += 2
                else:
                    res.append(raw[i]); i += 1
            node = StringLiteral(''.join(res)); node.span = span; return node
        if tok.type == TokenType.KEYWORD:
            if tok.value == 'true': node = BoolLiteral(True); node.span = span; return node
            if tok.value == 'false': node = BoolLiteral(False); node.span = span; return node
            if tok.value == 'na': node = Identifier('na'); node.span = span; return node
        if tok.type == TokenType.IDENTIFIER:
            parts = [tok.value]
            start_line, start_col = tok.line, tok.col
            while self._peek() and self._peek().type == TokenType.DOT:
                self._next()
                next_tok = self._expect(TokenType.IDENTIFIER)
                if next_tok:
                    parts.append(next_tok.value)
            if len(parts) > 1:
                node = QualifiedName(parts)
                end_tok = next_tok if len(parts) > 1 else tok
                node.span = SourceSpan(start_line, start_col, end_tok.line, end_tok.col + len(end_tok.value))
            else:
                node = Identifier(parts[0]); node.span = span
            return node
        if tok.type == TokenType.OPERATOR and tok.value in ('+', '-', 'not', '!'):
            operand = self.parse_expr(self._precedence(tok.value) + 1)
            if operand is None:
                if self._recovery_mode: return None
                raise SyntaxError(f"Expected operand after '{tok.value}'")
            node = UnaryOp(tok.value, operand); node.span = span; return node
        if tok.type == TokenType.BRACKET and tok.value == '(':
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
                if self._peek() and self._peek().type == TokenType.COMMA:
                    self._next()
            self._expect(TokenType.BRACKET, ']')
            # Determine if tuple literal or pattern (context)
            node = TupleLiteral(elements)
            node.span = span
            return node
        if tok.type == TokenType.UNKNOWN:
            if self._recovery_mode: return None
        self.pos -= 1
        return None

    def _parse_infix(self, left: ASTNode, op: str, prec: int) -> ASTNode:
        self._next()
        right = self.parse_expr(prec + 1 if not self._is_right_assoc(op) else prec)
        if right is None:
            if self._recovery_mode: return left
            raise SyntaxError(f"Expected right operand for '{op}'")
        node = BinaryOp(op, left, right)
        lspan = getattr(left, 'span', None)
        rspan = getattr(right, 'span', None)
        if lspan and rspan:
            node.span = SourceSpan(lspan.start_line, lspan.start_col, rspan.end_line, rspan.end_col)
        elif lspan:
            node.span = lspan
        return node

    def _parse_ternary(self, condition: ASTNode) -> ASTNode:
        self._next()
        then_expr = self.parse_expr(0)
        if then_expr is None:
            if self._recovery_mode: return condition
            raise SyntaxError("Expected expression after '?'")
        self._expect(TokenType.OPERATOR, ':')
        else_expr = self.parse_expr(0)
        if else_expr is None:
            if self._recovery_mode: return condition
            raise SyntaxError("Expected expression after ':'")
        node = TernaryOp(condition, then_expr, else_expr)
        cspan = getattr(condition, 'span', None)
        espan = getattr(else_expr, 'span', None)
        if cspan and espan:
            node.span = SourceSpan(cspan.start_line, cspan.start_col, espan.end_line, espan.end_col)
        return node

    def _parse_member_access(self, target: ASTNode) -> ASTNode:
        self._next()
        tok = self._expect(TokenType.IDENTIFIER)
        if not tok:
            return target
        node = MemberAccess(target, tok.value)
        tspan = getattr(target, 'span', None)
        if tspan:
            node.span = SourceSpan(tspan.start_line, tspan.start_col, tok.line, tok.col + len(tok.value))
        return node

    def _parse_index(self, target: ASTNode) -> ASTNode:
        self._next()
        idx = self.parse_expr(0)
        if idx is None:
            if self._recovery_mode: return target
            raise SyntaxError("Expected expression inside '[]'")
        self._expect(TokenType.BRACKET, ']')
        node = Index(target, idx)
        tspan = getattr(target, 'span', None)
        if tspan:
            node.span = SourceSpan(tspan.start_line, tspan.start_col, tspan.end_line, tspan.end_col + 1)
        return node

    def _parse_call(self, func: ASTNode) -> ASTNode:
        self._next()
        args = []
        start_tok = self._peek()
        while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == ')'):
            self._skip_comments_and_newlines()
            arg = self.parse_expr(0)
            if arg is None: break
            args.append(arg)
            if self._peek() and self._peek().type == TokenType.COMMA:
                self._next()
        end_tok = self._peek()
        self._expect(TokenType.BRACKET, ')')
        node = Call(func, args)
        fspan = getattr(func, 'span', None)
        if fspan and end_tok:
            node.span = SourceSpan(fspan.start_line, fspan.start_col, end_tok.line, end_tok.col + 1)
        elif fspan:
            node.span = fspan
        return node

    def _parse_generic_type(self, base: ASTNode) -> ASTNode:
        self._next()  # '<'
        params = []
        while self._peek() and self._peek().type != TokenType.OPERATOR or self._peek().value != '>':
            self._skip_comments_and_newlines()
            param = self.parse_expr(0)
            if param is None: break
            params.append(param)
            if self._peek() and self._peek().type == TokenType.COMMA:
                self._next()
        self._expect(TokenType.OPERATOR, '>')
        node = GenericType('', params)
        node.span = getattr(base, 'span', None)
        return node

    # ─── Statement ────────────────────────────────────────────────
    def parse_statement(self) -> Optional[ASTNode]:
        self._skip_comments_and_newlines()
        tok = self._peek()
        if not tok:
            return None

        # Directive
        if tok.type == TokenType.DIRECTIVE:
            self._next()
            node = Directive(tok.value, tok.value)
            node.span = SourceSpan(tok.line, tok.col, tok.line, tok.col + len(tok.value))
            return node

        # Function declaration: identifier ( params ) =>
        if tok.type == TokenType.IDENTIFIER and self._looks_like_function_declaration():
            return self._parse_function_decl()

        if tok.type == TokenType.KEYWORD:
            if tok.value in ('var', 'varip'):
                return self._parse_var_decl()
            if tok.value == 'const':
                return self._parse_const_decl()
            if tok.value == 'type':
                return self._parse_type_decl()
            if tok.value == 'enum':
                return self._parse_enum_decl()
            if tok.value == 'method':
                return self._parse_method_decl()
            if tok.value == 'import':
                return self._parse_import()
            if tok.value == 'if':
                return self._parse_if()
            if tok.value == 'for':
                return self._parse_for()
            if tok.value == 'while':
                return self._parse_while()
            if tok.value == 'switch':
                return self._parse_switch()
            if tok.value == 'return':
                return self._parse_return()

        # Expression/assignment
        start_tok = self._peek()
        left_expr = self.parse_expr(0)
        if left_expr is None:
            return None

        # Destructuring: [a,b] = value
        if isinstance(left_expr, TupleLiteral):
            if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value in ('=', ':='):
                op = self._next()
                value = self.parse_expr(0)
                if value is None:
                    if self._recovery_mode:
                        self._skip_until_sync(); return None
                    raise SyntaxError("Expected value after assignment")
                node = DestructuringAssignment(left_expr.elements, value)
                node.span = getattr(left_expr, 'span', None)
                return node

        # Simple assignment
        tok = self._peek()
        if tok and tok.type == TokenType.OPERATOR and tok.value in ('=', ':=', '+=', '-=', '*=', '/=', '%='):
            self._next()
            value = self.parse_expr(0)
            if value is None:
                if self._recovery_mode:
                    self._skip_until_sync(); return None
                raise SyntaxError(f"Expected value after '{tok.value}'")
            node = Assignment(left_expr, value, tok.value)
            lspan = getattr(left_expr, 'span', None)
            if lspan:
                node.span = lspan
            return node

        node = ExpressionStatement(left_expr)
        node.span = getattr(left_expr, 'span', None)
        return node

    def _looks_like_function_declaration(self) -> bool:
        if self.pos + 1 >= len(self.tokens):
            return False
        if self.tokens[self.pos + 1].type != TokenType.BRACKET or self.tokens[self.pos + 1].value != '(':
            return False
        depth, i = 0, self.pos + 1
        while i < len(self.tokens):
            tok = self.tokens[i]
            if tok.type == TokenType.BRACKET:
                if tok.value == '(':
                    depth += 1
                elif tok.value == ')':
                    depth -= 1
                    if depth == 0:
                        if i + 1 < len(self.tokens) and self.tokens[i + 1].type == TokenType.OPERATOR and self.tokens[i + 1].value == '=>':
                            return True
                        return False
            i += 1
        return False

    def _parse_block(self, require_indent: bool = True) -> List[ASTNode]:
        self._skip_comments_and_newlines()
        stmts = []
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '{':
            self._next()
            while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == '}'):
                stmt = self.parse_statement()
                if stmt: stmts.append(stmt)
                self._skip_comments_and_newlines()
            self._expect(TokenType.BRACKET, '}')
            return stmts

        if require_indent and self._peek() and self._peek().type == TokenType.INDENT:
            self._next()
            while self._peek() and self._peek().type not in (TokenType.DEDENT, TokenType.EOF):
                stmt = self.parse_statement()
                if stmt: stmts.append(stmt)
                self._skip_comments_and_newlines()
            if self._peek() and self._peek().type == TokenType.DEDENT:
                self._next()
        else:
            stmt = self.parse_statement()
            if stmt: stmts.append(stmt)
        return stmts

    def _parse_var_decl(self) -> VarDeclaration:
        tok = self._expect(TokenType.KEYWORD)
        varip = tok.value == 'varip'
        typ = None
        if self._peek() and self._peek().type == TokenType.IDENTIFIER:
            typ_tok = self._peek()
            if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == TokenType.IDENTIFIER:
                self._next()
                typ = Identifier(typ_tok.value)
        name_tok = self._expect(TokenType.IDENTIFIER)
        value = None
        if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value in ('=', ':='):
            self._next()
            value = self.parse_expr(0)
        node = VarDeclaration(varip, typ, name_tok.value, value)
        if name_tok:
            node.span = SourceSpan(name_tok.line, name_tok.col, name_tok.line, name_tok.col + len(name_tok.value))
        return node

    def _parse_const_decl(self) -> ConstDeclaration:
        self._expect(TokenType.KEYWORD, 'const')
        name_tok = self._expect(TokenType.IDENTIFIER)
        self._expect(TokenType.OPERATOR, '=')
        value = self.parse_expr(0)
        if value is None:
            if self._recovery_mode:
                value = IntegerLiteral(0)
            else:
                raise SyntaxError(f"Expected value for const '{name_tok.value}'")
        node = ConstDeclaration(name_tok.value, value)
        if name_tok:
            node.span = SourceSpan(name_tok.line, name_tok.col, name_tok.line, name_tok.col + len(name_tok.value))
        return node

    def _parse_type_decl(self) -> TypeDeclaration:
        self._expect(TokenType.KEYWORD, 'type')
        name_tok = self._expect(TokenType.IDENTIFIER)
        fields = []
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '{':
            self._next()
            while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == '}'):
                self._skip_comments_and_newlines()
                typ_tok = self._expect(TokenType.IDENTIFIER)
                field_name = self._expect(TokenType.IDENTIFIER)
                if typ_tok and field_name:
                    fields.append((typ_tok.value, field_name.value))
                if self._peek() and self._peek().type == TokenType.COMMA:
                    self._next()
            self._expect(TokenType.BRACKET, '}')
        else:
            self._skip_comments_and_newlines()
            if self._peek() and self._peek().type == TokenType.INDENT:
                self._next()
            while self._peek() and self._peek().type not in (TokenType.DEDENT, TokenType.EOF):
                self._skip_comments_and_newlines()
                typ_tok = self._peek()
                if typ_tok and typ_tok.type == TokenType.IDENTIFIER:
                    self._next()
                    field_name = self._expect(TokenType.IDENTIFIER)
                    if field_name:
                        fields.append((typ_tok.value, field_name.value))
                else:
                    break
            if self._peek() and self._peek().type == TokenType.DEDENT:
                self._next()
        node = TypeDeclaration(name_tok.value, fields)
        if name_tok:
            node.span = SourceSpan(name_tok.line, name_tok.col, name_tok.line, name_tok.col + len(name_tok.value))
        return node

    def _parse_enum_decl(self) -> EnumDeclaration:
        self._expect(TokenType.KEYWORD, 'enum')
        name_tok = self._expect(TokenType.IDENTIFIER)
        values = []
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '{':
            self._next()
            while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == '}'):
                self._skip_comments_and_newlines()
                val_tok = self._expect(TokenType.IDENTIFIER)
                if val_tok: values.append(val_tok.value)
                if self._peek() and self._peek().type == TokenType.COMMA:
                    self._next()
            self._expect(TokenType.BRACKET, '}')
        else:
            self._skip_comments_and_newlines()
            if self._peek() and self._peek().type == TokenType.INDENT:
                self._next()
            while self._peek() and self._peek().type not in (TokenType.DEDENT, TokenType.EOF):
                val_tok = self._expect(TokenType.IDENTIFIER)
                if val_tok: values.append(val_tok.value)
                if self._peek() and self._peek().type == TokenType.COMMA:
                    self._next()
                self._skip_comments_and_newlines()
            if self._peek() and self._peek().type == TokenType.DEDENT:
                self._next()
        node = EnumDeclaration(name_tok.value, values)
        if name_tok:
            node.span = SourceSpan(name_tok.line, name_tok.col, name_tok.line, name_tok.col + len(name_tok.value))
        return node

    def _parse_params(self) -> List[Dict[str, Optional[ASTNode]]]:
        self._expect(TokenType.BRACKET, '(')
        params = []
        while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == ')'):
            self._skip_comments_and_newlines()
            if not self._peek(): break
            typ = None
            if self._peek().type == TokenType.IDENTIFIER:
                typ_tok = self._peek()
                if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == TokenType.IDENTIFIER:
                    self._next()
                    typ = Identifier(typ_tok.value)
            name_tok = self._expect(TokenType.IDENTIFIER)
            default = None
            if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '=':
                self._next()
                default = self.parse_expr(0)
            if name_tok:
                params.append({'name': name_tok.value, 'type': typ, 'default': default})
            if self._peek() and self._peek().type == TokenType.COMMA:
                self._next()
        self._expect(TokenType.BRACKET, ')')
        return params

    def _parse_method_decl(self) -> MethodDeclaration:
        self._expect(TokenType.KEYWORD, 'method')
        name_tok = self._expect(TokenType.IDENTIFIER)
        params = self._parse_params()
        self._expect(TokenType.OPERATOR, '=>')
        body = None
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '{':
            body = self._parse_block()
        else:
            body = self.parse_expr(0)
        node = MethodDeclaration(name_tok.value, params, body)
        if name_tok:
            node.span = SourceSpan(name_tok.line, name_tok.col, name_tok.line, name_tok.col + len(name_tok.value))
        return node

    def _parse_function_decl(self) -> FunctionDeclaration:
        name_tok = self._expect(TokenType.IDENTIFIER)
        params = self._parse_params()
        if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value == '=>':
            self._next()
        body = None
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '{':
            body = self._parse_block()
        else:
            body = self.parse_expr(0)
        node = FunctionDeclaration(name_tok.value, params, body)
        if name_tok:
            node.span = SourceSpan(name_tok.line, name_tok.col, name_tok.line, name_tok.col + len(name_tok.value))
        return node

    def _parse_import(self) -> ImportDeclaration:
        self._expect(TokenType.KEYWORD, 'import')
        path_tokens = []
        while self._peek() and self._peek().type not in (TokenType.NEWLINE, TokenType.COMMENT, TokenType.EOF):
            path_tokens.append(self._next())
        path = ' '.join(t.value for t in path_tokens if t)
        node = ImportDeclaration(path)
        return node

    def _parse_if(self) -> IfStatement:
        self._expect(TokenType.KEYWORD, 'if')
        start_tok = self._peek()
        condition = self.parse_expr(0)
        if condition is None:
            if self._recovery_mode: return None
            raise SyntaxError("Expected condition after 'if'")
        then_body = self._parse_block()
        else_body = []
        self._skip_comments_and_newlines()
        if self._peek() and self._peek().type == TokenType.KEYWORD and self._peek().value == 'else':
            self._next()
            else_body = self._parse_block()
        node = IfStatement(condition, then_body, else_body)
        end_tok = self.tokens[self.pos-1] if self.pos > 0 else None
        if start_tok and end_tok:
            node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col + 1)
        return node

    def _parse_for(self) -> ForStatement:
        self._expect(TokenType.KEYWORD, 'for')
        start_tok = self._peek()
        iterator = self._expect(TokenType.IDENTIFIER)
        # Check for 'in' variant: for x in array
        if self._peek() and self._peek().type == TokenType.KEYWORD and self._peek().value == 'in':
            self._next()
            iterable = self.parse_expr(0)
            if iterable is None:
                if self._recovery_mode: return None
                raise SyntaxError("Expected iterable after 'in'")
        else:
            # for i = 1 to 10
            self._expect(TokenType.OPERATOR, '=')
            start = self.parse_expr(0)
            if start is None:
                if self._recovery_mode: return None
                raise SyntaxError("Expected start value after '='")
            step = None
            if self._peek() and self._peek().type == TokenType.KEYWORD and self._peek().value == 'by':
                self._next()
                step = self.parse_expr(0)
            if self._peek() and self._peek().type == TokenType.KEYWORD and self._peek().value == 'to':
                self._next()
                end = self.parse_expr(0)
                if end is None:
                    if self._recovery_mode:
                        end = IntegerLiteral(0)
                    else:
                        raise SyntaxError("Expected end value after 'to'")
                iterable = RangeExpr(start, end, step)
                if start_tok and end:
                    iterable.span = SourceSpan(start_tok.line, start_tok.col, end.line, end.col + 1)
            else:
                iterable = start
        body = self._parse_block()
        node = ForStatement(Identifier(iterator.value), iterable, body)
        if iterator:
            node.span = SourceSpan(iterator.line, iterator.col, iterator.line, iterator.col + len(iterator.value))
        return node

    def _parse_while(self) -> WhileStatement:
        self._expect(TokenType.KEYWORD, 'while')
        start_tok = self._peek()
        condition = self.parse_expr(0)
        if condition is None:
            if self._recovery_mode: return None
            raise SyntaxError("Expected condition after 'while'")
        body = self._parse_block()
        node = WhileStatement(condition, body)
        end_tok = self.tokens[self.pos-1] if self.pos > 0 else None
        if start_tok and end_tok:
            node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col + 1)
        return node

    def _parse_switch(self) -> SwitchStatement:
        self._expect(TokenType.KEYWORD, 'switch')
        start_tok = self._peek()
        value = self.parse_expr(0)
        if value is None:
            if self._recovery_mode: return None
            raise SyntaxError("Expected value after 'switch'")
        cases, default_body = [], []
        self._skip_comments_and_newlines()
        if self._peek() and self._peek().type == TokenType.BRACKET and self._peek().value == '{':
            self._next()
            while self._peek() and not (self._peek().type == TokenType.BRACKET and self._peek().value == '}'):
                self._skip_comments_and_newlines()
                if self._peek() and self._peek().type == TokenType.KEYWORD and self._peek().value == 'default':
                    self._next()
                    if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value in ('=>', ':'):
                        self._next()
                    default_body = self._parse_block()
                elif self._peek() and self._peek().type == TokenType.KEYWORD and self._peek().value == 'case':
                    self._next()
                    case_value = self.parse_expr(0)
                    if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value in ('=>', ':'):
                        self._next()
                    body = self._parse_block()
                    if case_value is not None:
                        cases.append((case_value, body))
                elif self._peek() and self._peek().type == TokenType.NUMBER:
                    # Pine: switch x 1 => 2 =>
                    num = self.parse_expr(0)
                    if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value in ('=>', ':'):
                        self._next()
                        body = self._parse_block()
                        if num is not None:
                            cases.append((num, body))
                else:
                    break
            self._expect(TokenType.BRACKET, '}')
        else:
            if self._peek() and self._peek().type == TokenType.INDENT:
                self._next()
            while self._peek() and self._peek().type not in (TokenType.DEDENT, TokenType.EOF):
                self._skip_comments_and_newlines()
                if self._peek() and self._peek().type == TokenType.KEYWORD and self._peek().value == 'default':
                    self._next()
                    if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value in ('=>', ':'):
                        self._next()
                    default_body = self._parse_block()
                elif self._peek() and self._peek().type == TokenType.KEYWORD and self._peek().value == 'case':
                    self._next()
                    case_value = self.parse_expr(0)
                    if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value in ('=>', ':'):
                        self._next()
                    body = self._parse_block()
                    if case_value is not None:
                        cases.append((case_value, body))
                elif self._peek() and self._peek().type == TokenType.NUMBER:
                    num = self.parse_expr(0)
                    if self._peek() and self._peek().type == TokenType.OPERATOR and self._peek().value in ('=>', ':'):
                        self._next()
                        body = self._parse_block()
                        if num is not None:
                            cases.append((num, body))
                else:
                    break
            if self._peek() and self._peek().type == TokenType.DEDENT:
                self._next()
        node = SwitchStatement(value, cases, default_body)
        end_tok = self.tokens[self.pos-1] if self.pos > 0 else None
        if start_tok and end_tok:
            node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col + 1)
        return node

    def _parse_return(self) -> ReturnStatement:
        self._expect(TokenType.KEYWORD, 'return')
        start_tok = self._peek()
        value = self.parse_expr(0)
        node = ReturnStatement(value)
        if start_tok:
            end_tok = self.tokens[self.pos-1] if self.pos > 0 else start_tok
            node.span = SourceSpan(start_tok.line, start_tok.col, end_tok.line, end_tok.col + 1)
        return node

# ─── PINEAST WRAPPER ─────────────────────────────────────────────
class PineAST:
    def __init__(self, code: str):
        self.code = code
        self.tokens = PineTokenizer(code).get_tokens()
        self.parser = PrattParser(self.tokens, recovery=True)
        self.root = self._parse_module()
        self._extract_symbols()

    def _parse_module(self) -> Module:
        body = []
        while self.parser._peek() and self.parser._peek().type != TokenType.EOF:
            try:
                stmt = self.parser.parse_statement()
                if stmt:
                    body.append(stmt)
            except SyntaxError:
                self.parser._skip_until_sync()
                continue
            self.parser._skip_comments_and_newlines()
        return Module(body)

    def _extract_symbols(self):
        self.symbols: Dict[str, str] = {}
        self.arrays: List[str] = []
        self.matrices: List[str] = []
        self.constants: Dict[str, Any] = {}
        self.functions: List[str] = []
        self.types: List[Dict] = []
        self.enums: List[Dict] = []
        self.methods: List[Dict] = []
        self.imports: List[str] = []
        self.directives: List[Dict] = []

        for node in self.root.body:
            if isinstance(node, VarDeclaration):
                name = node.name
                if name:
                    if node.value and isinstance(node.value, Call):
                        func = node.value.func
                        if isinstance(func, QualifiedName) and func.parts and func.parts[0] == 'array':
                            self.symbols[name] = 'array'
                            self.arrays.append(name)
                        elif isinstance(func, QualifiedName) and func.parts and func.parts[0] == 'matrix':
                            self.symbols[name] = 'matrix'
                            self.matrices.append(name)
                        else:
                            self.symbols[name] = 'var'
                    else:
                        self.symbols[name] = 'var'
            elif isinstance(node, ConstDeclaration):
                name = node.name
                if isinstance(node.value, IntegerLiteral):
                    self.constants[name] = node.value.value
                    self.symbols[name] = 'const'
                elif isinstance(node.value, FloatLiteral):
                    self.constants[name] = node.value.value
                    self.symbols[name] = 'const'
                else:
                    self.symbols[name] = 'const'
            elif isinstance(node, FunctionDeclaration):
                self.functions.append(node.name)
                self.symbols[node.name] = 'function'
            elif isinstance(node, TypeDeclaration):
                self.types.append({'name': node.name, 'fields': node.fields})
                self.symbols[node.name] = 'type'
            elif isinstance(node, EnumDeclaration):
                self.enums.append({'name': node.name, 'values': node.values})
                self.symbols[node.name] = 'enum'
            elif isinstance(node, MethodDeclaration):
                self.methods.append({'name': node.name, 'params': node.params})
                self.symbols[node.name] = 'method'
            elif isinstance(node, ImportDeclaration):
                self.imports.append(node.path)
                self.symbols[f"import_{node.path}"] = 'import'
            elif isinstance(node, Directive):
                self.directives.append({'name': node.name, 'value': node.value})

    def get_symbols(self) -> Dict[str, str]:
        return self.symbols
    def get_arrays(self) -> List[str]:
        return self.arrays
    def get_matrices(self) -> List[str]:
        return self.matrices
    def get_constants(self) -> Dict[str, Any]:
        return self.constants
    def get_functions(self) -> List[str]:
        return self.functions
    def get_types(self) -> List[Dict]:
        return self.types
    def get_enums(self) -> List[Dict]:
        return self.enums
    def get_methods(self) -> List[Dict]:
        return self.methods
    def get_imports(self) -> List[str]:
        return self.imports
    def get_directives(self) -> List[Dict]:
        return self.directives
    def get_root(self) -> Module:
        return self.root

if __name__ == "__main__":
    code = """
//@version=6
indicator("Test")
type Features
    float value
    float slope
enum Status { NAIK, TURUN, DATAR }
method sum(Weights w) => w.value + w.slope
var int counter = 0
const MAX = 100
f_test() => true
ta.ema(close, 14)
if close > open
    plot(close)
else
    plot(open)
for i = 1 to 10
    x := x + i
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
