#!/usr/bin/env python3
"""Context Builder — Bangun AuditContext dengan AST traversal yang benar."""
import re
from engine.parser import (
    ASTNode, Module, VarDeclaration, TypeDeclaration,
    MethodDeclaration, FunctionDeclaration, Call,
    Identifier, MemberAccess, SwitchStatement
)
from engine.audit.context import AuditContext

def _walk_all_children(node):
    """Traversal generik: kunjungi SEMUA atribut node."""
    yield node
    if isinstance(node, list):
        for item in node: yield from _walk_all_children(item)
        return
    if not hasattr(node, '__dict__'): return
    for attr, value in vars(node).items():
        if attr.startswith('_'): continue
        if isinstance(value, ASTNode):
            yield from _walk_all_children(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, ASTNode):
                    yield from _walk_all_children(item)

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
    return ''.join(v for t, v in _tokenize(code) if t != 'COMMENT')

def build_context(ast: ASTNode, code: str) -> AuditContext:
    clean = _strip_comments(code)
    all_nodes = list(_walk_all_children(ast))
    lines = code.split('\n')

    types_count = sum(1 for n in all_nodes if isinstance(n, TypeDeclaration))
    methods_count = sum(1 for n in all_nodes if isinstance(n, MethodDeclaration))
    func_count = sum(1 for n in all_nodes if isinstance(n, FunctionDeclaration))
    var_count = sum(1 for n in all_nodes if isinstance(n, VarDeclaration))
    switch_count = sum(1 for n in all_nodes if isinstance(n, SwitchStatement))

    # Global var count: hanya dari Module.body langsung
    global_var_count = 0
    if isinstance(ast, Module) and hasattr(ast, 'body'):
        global_var_count = sum(1 for n in ast.body if isinstance(n, VarDeclaration))

    call_names = []
    for n in all_nodes:
        if isinstance(n, Call):
            if isinstance(n.func, Identifier):
                call_names.append(n.func.name)
            elif isinstance(n.func, MemberAccess):
                path = []; cur = n.func
                while isinstance(cur, MemberAccess):
                    path.append(cur.member); cur = cur.target
                if isinstance(cur, Identifier): path.append(cur.name)
                call_names.append('.'.join(reversed(path)))

    return AuditContext(
        barstate_guard=bool(re.search(r'\bbarstate\.(isconfirmed|ishistory)\b', clean)),
        na_guard=bool(re.search(r'\bna\(', clean)),
        nz_guard=bool(re.search(r'\bnz\(', clean)),
        nan_check=bool(re.search(r'\bmath\.(is_nan|is_finite)\(', clean)),
        var_count=var_count,
        global_var_count=global_var_count,
        array_eviction=any('array.push' in c for c in call_names) and any(c in call_names for c in ['array.shift', 'array.pop']),
        matrix_eviction=any('matrix.add_row' in c for c in call_names) and any('matrix.remove_row' in c for c in call_names),
        drawing_limits=bool(re.search(r'\bmax_(labels|lines|boxes)_count\s*=', clean)),
        bars_back_limit=bool(re.search(r'\bmax_bars_back\s*=', clean)),
        cached_sec=bool(re.search(r'\bvar\b', clean) and 'request.security' in call_names),
        step_loop=bool(re.search(r'\bfor\b', clean) and re.search(r'\bby\b', clean)),
        force_overlay=bool(re.search(r'\bforce_overlay\s*=\s*true\b', clean)),
        hidden_plot=bool(re.search(r'\bdisplay\s*=\s*display\.none\b', clean)),
        inline_inputs=bool(re.search(r'\binline\s*=', clean)),
        transparency=bool(re.search(r'\bcolor\.new\(', clean)),
        alert_cond='alertcondition' in call_names,
        alert_func='alert' in call_names,
        logging=bool(re.search(r'\blog\.(info|warning|error)\(', clean)),
        export=bool(re.search(r'\bexport\b', clean)),
        typed_inputs=bool(re.search(r'\binput\.(int|float|bool|color|source|price|time)\(', clean)),
        typed_fields=False,
        tooltip_count=len(re.findall(r'\btooltip\s*=', clean)),
        input_groups=bool(re.search(r'\bgroup\s*=', clean)),
        structured_comments=bool(re.search(r'//\s*~~', code)),
        documented_code=len(lines) > 100 and sum(1 for l in lines if l.strip().startswith('//')) > 20,
        types_count=types_count,
        methods_count=methods_count,
        func_count=func_count,
        switch_count=switch_count,
        total_lines=len(lines),
        code_lines=sum(1 for l in lines if l.strip() and not l.strip().startswith('//')),
        comment_lines=sum(1 for l in lines if l.strip().startswith('//')),
        call_names=call_names,
    )
