#!/usr/bin/env python3
"""Context Builder — Bangun AuditContext dari AST dan kode sumber."""
import re
from typing import Dict, Any
from engine.parser import (
    ASTNode, Module, VarDeclaration, TypeDeclaration,
    MethodDeclaration, FunctionDeclaration, Call,
    Identifier, MemberAccess, SwitchStatement
)

def _walk(node):
    yield node
    if isinstance(node, list):
        for item in node: yield from _walk(item)
        return
    if not hasattr(node, '__dict__'): return
    for value in vars(node).values():
        if isinstance(value, ASTNode):
            yield from _walk(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, ASTNode):
                    yield from _walk(item)

def _tokenize(code: str) -> list:
    tokens = []
    i = 0
    while i < len(code):
        if code[i] in ('"', "'"):
            quote = code[i]; j = i + 1
            while j < len(code) and code[j] != quote:
                if code[j] == '\\': j += 1
                j += 1
            tokens.append(('STRING', code[i:j+1])); i = j + 1; continue
        if code[i:i+2] == '//':
            j = i
            while j < len(code) and code[j] != '\n': j += 1
            tokens.append(('COMMENT', code[i:j])); i = j; continue
        if code[i:i+2] == '/*':
            j = i + 2
            while j < len(code) and code[j:j+2] != '*/': j += 1
            tokens.append(('COMMENT', code[i:j+2])); i = j + 2; continue
        if code[i].isalpha() or code[i] == '_':
            j = i
            while j < len(code) and (code[j].isalnum() or code[j] == '_'): j += 1
            tokens.append(('IDENT', code[i:j])); i = j; continue
        tokens.append(('SYMBOL', code[i])); i += 1
    return tokens

def _strip_comments(code: str) -> str:
    tokens = _tokenize(code)
    return ''.join(v for t, v in tokens if t != 'COMMENT')

def build_context(ast: ASTNode, code: str) -> Dict[str, Any]:
    clean = _strip_comments(code)
    ctx = {}
    all_nodes = list(_walk(ast))

    # AST counts
    ctx['types_count'] = sum(1 for n in all_nodes if isinstance(n, TypeDeclaration))
    ctx['methods_count'] = sum(1 for n in all_nodes if isinstance(n, MethodDeclaration))
    ctx['func_count'] = sum(1 for n in all_nodes if isinstance(n, FunctionDeclaration))
    ctx['var_count'] = sum(1 for n in all_nodes if isinstance(n, VarDeclaration))
    ctx['global_var_count'] = sum(1 for n in ast.body if isinstance(n, VarDeclaration)) if hasattr(ast, 'body') else 0
    ctx['switch_count'] = sum(1 for n in all_nodes if isinstance(n, SwitchStatement))

    # Call detection
    call_names = set()
    for n in all_nodes:
        if isinstance(n, Call):
            if isinstance(n.func, Identifier):
                call_names.add(n.func.name)
            elif isinstance(n.func, MemberAccess):
                path = []; cur = n.func
                while isinstance(cur, MemberAccess):
                    path.append(cur.member); cur = cur.target
                if isinstance(cur, Identifier): path.append(cur.name)
                call_names.add('.'.join(reversed(path)))
    ctx['alert_cond'] = 'alertcondition' in call_names
    ctx['alert_func'] = 'alert' in call_names
    ctx['array_eviction'] = any('array.push' in c for c in call_names) and any(c in call_names for c in ['array.shift', 'array.pop'])
    ctx['matrix_eviction'] = any('matrix.add_row' in c for c in call_names) and any('matrix.remove_row' in c for c in call_names)

    # Regex-based (on clean code)
    ctx['barstate_guard'] = bool(re.search(r'\bbarstate\.(isconfirmed|ishistory)\b', clean))
    ctx['na_guard'] = bool(re.search(r'\bna\(', clean))
    ctx['nz_guard'] = bool(re.search(r'\bnz\(', clean))
    ctx['nan_check'] = bool(re.search(r'\bmath\.(is_nan|is_finite)\(', clean))
    ctx['drawing_limits'] = bool(re.search(r'\bmax_(labels|lines|boxes)_count\s*=', clean))
    ctx['bars_back_limit'] = bool(re.search(r'\bmax_bars_back\s*=', clean))
    ctx['cached_sec'] = bool(re.search(r'\bvar\b', clean) and 'request.security' in call_names)
    ctx['step_loop'] = bool(re.search(r'\bfor\b', clean) and re.search(r'\bby\b', clean))
    ctx['force_overlay'] = bool(re.search(r'\bforce_overlay\s*=\s*true\b', clean))
    ctx['hidden_plot'] = bool(re.search(r'\bdisplay\s*=\s*display\.none\b', clean))
    ctx['logging'] = bool(re.search(r'\blog\.(info|warning|error)\(', clean))
    ctx['export'] = bool(re.search(r'\bexport\b', clean))
    ctx['typed_inputs'] = bool(re.search(r'\binput\.(int|float|bool|color|source|price|time)\(', clean))
    ctx['tooltip_count'] = len(re.findall(r'\btooltip\s*=', clean))
    ctx['input_groups'] = bool(re.search(r'\bgroup\s*=', clean))
    ctx['structured_comments'] = bool(re.search(r'//\s*~~', code))
    ctx['documented_code'] = len(code.split('\n')) > 100 and sum(1 for l in code.split('\n') if l.strip().startswith('//')) > 20

    return ctx
