#!/usr/bin/env python3
"""
Control Flow Graph v2.4 — Correct loop body tracking, safe dominator
"""
from typing import List, Dict, Set, Optional, Tuple
from engine.parser import (
    ASTNode, Module, IfStatement, ForStatement, ForInStatement, WhileStatement,
    SwitchStatement, ReturnStatement, BreakStatement, ContinueStatement,
    FunctionDeclaration, MethodDeclaration
)

class BasicBlock:
    _id_counter = 0
    def __init__(self, label: str = None):
        BasicBlock._id_counter += 1
        self.id = BasicBlock._id_counter
        self.label = label or f"bb{self.id}"
        self.statements: List[ASTNode] = []
        self.successors: List['BasicBlock'] = []
        self.predecessors: List['BasicBlock'] = []
        self.idominator: Optional['BasicBlock'] = None
        self.dominates: Set['BasicBlock'] = set()
        self.is_entry = False
        self.is_exit = False

    def add_successor(self, block: 'BasicBlock'):
        if block not in self.successors:
            self.successors.append(block)
            block.predecessors.append(self)

class LoopInfo:
    def __init__(self, header: BasicBlock, exit_block: BasicBlock):
        self.header = header
        self.body_blocks: Set[BasicBlock] = set()  # diisi setelah proses body
        self.exit_block = exit_block
        self.back_edges: List[Tuple[BasicBlock, BasicBlock]] = []

class CFG:
    def __init__(self):
        self.entry: Optional[BasicBlock] = None
        self.exit: BasicBlock = BasicBlock("exit")
        self.exit.is_exit = True
        self.blocks: List[BasicBlock] = []
        self.loops: List[LoopInfo] = []

    def create_block(self, label: str = None) -> BasicBlock:
        block = BasicBlock(label)
        self.blocks.append(block)
        return block

    def compute_dominators(self):
        if not self.entry:
            return
        all_blocks = list(set(self.blocks) | {self.exit})
        visited = set()
        postorder = []
        def dfs(b):
            if b in visited: return
            visited.add(b)
            for s in b.successors:
                dfs(s)
            postorder.append(b)
        dfs(self.entry)
        blocks = list(reversed(postorder))
        block_to_idx = {b: i for i, b in enumerate(blocks)}
        idom = [None] * len(blocks)
        if self.entry in block_to_idx:
            idom[block_to_idx[self.entry]] = self.entry
        changed = True
        while changed:
            changed = False
            for b in blocks:
                if b == self.entry:
                    continue
                preds = [p for p in b.predecessors if p in block_to_idx]
                if not preds:
                    continue
                new_idom = preds[0]
                for p in preds[1:]:
                    if idom[block_to_idx[p]] is not None:
                        new_idom = self._intersect(p, new_idom, idom, block_to_idx)
                if idom[block_to_idx[b]] != new_idom:
                    idom[block_to_idx[b]] = new_idom
                    changed = True
        for i, b in enumerate(blocks):
            if idom[i] is not None and idom[i] != b:
                b.idominator = idom[i]
                b.idominator.dominates.add(b)

    def _intersect(self, b1: BasicBlock, b2: BasicBlock, idom, block_to_idx) -> BasicBlock:
        finger1 = b1
        finger2 = b2
        max_iter = len(block_to_idx) * 2
        iter_count = 0
        while finger1 != finger2 and iter_count < max_iter:
            iter_count += 1
            idx1 = block_to_idx.get(finger1, -1)
            idx2 = block_to_idx.get(finger2, -1)
            while idx1 > idx2 and idx1 >= 0 and idx2 >= 0:
                finger1 = idom[idx1]
                if finger1 is None: return b1
                idx1 = block_to_idx.get(finger1, -1)
            while idx2 > idx1 and idx1 >= 0 and idx2 >= 0:
                finger2 = idom[idx2]
                if finger2 is None: return b2
                idx2 = block_to_idx.get(finger2, -1)
        return finger1

def build_cfg(func_node: ASTNode) -> CFG:
    cfg = CFG()
    entry = cfg.create_block("entry")
    entry.is_entry = True
    cfg.entry = entry

    loop_stack: List[Tuple[LoopInfo, BasicBlock, BasicBlock]] = []  # (loop_info, header, after)

    def process_statements(stmts: List[ASTNode], start_block: BasicBlock,
                           break_target: Optional[BasicBlock] = None,
                           continue_target: Optional[BasicBlock] = None) -> BasicBlock:
        current = start_block
        for stmt in stmts:
            if isinstance(stmt, IfStatement):
                then_block = cfg.create_block("if_then")
                else_block = cfg.create_block("if_else") if stmt.else_body else None
                merge_block = cfg.create_block("if_merge")
                current.add_successor(then_block)
                if else_block:
                    current.add_successor(else_block)
                else:
                    current.add_successor(merge_block)
                then_end = process_statements(stmt.then_body, then_block, break_target, continue_target)
                then_end.add_successor(merge_block)
                if else_block and stmt.else_body:
                    else_end = process_statements(stmt.else_body, else_block, break_target, continue_target)
                    else_end.add_successor(merge_block)
                current = merge_block
            elif isinstance(stmt, (ForStatement, ForInStatement, WhileStatement)):
                loop_header = cfg.create_block("loop_header")
                loop_body_start = cfg.create_block("loop_body")
                loop_after = cfg.create_block("loop_after")
                if hasattr(stmt, 'condition'):
                    loop_header.statements.append(stmt.condition)
                current.add_successor(loop_header)
                loop_header.add_successor(loop_body_start)
                loop_header.add_successor(loop_after)
                
                # Buat loop info
                loop_info = LoopInfo(loop_header, loop_after)
                loop_info.body_blocks.add(loop_header)  # header adalah bagian dari loop
                loop_info.body_blocks.add(loop_body_start)
                
                loop_stack.append((loop_info, loop_header, loop_after))
                
                # Proses body
                body_end = process_statements(stmt.body, loop_body_start, break_target=loop_after, continue_target=loop_header)
                body_end.add_successor(loop_header)  # back edge
                
                loop_stack.pop()
                
                # Kumpulkan semua blok di body (antara body_start dan back edge)
                # Sederhana: tambahkan semua blok yang dibuat selama pemrosesan body
                for blk in cfg.blocks:
                    if blk not in loop_info.body_blocks and blk != loop_after:
                        if blk.predecessors and any(p in loop_info.body_blocks for p in blk.predecessors):
                            loop_info.body_blocks.add(blk)
                
                loop_info.back_edges.append((body_end, loop_header))
                cfg.loops.append(loop_info)
                current = loop_after
            elif isinstance(stmt, SwitchStatement):
                switch_merge = cfg.create_block("switch_merge")
                for case_val, case_body in stmt.cases:
                    case_block = cfg.create_block("switch_case")
                    current.add_successor(case_block)
                    case_end = process_statements(case_body, case_block, break_target=switch_merge, continue_target=continue_target)
                    case_end.add_successor(switch_merge)
                if stmt.default_body:
                    default_block = cfg.create_block("switch_default")
                    current.add_successor(default_block)
                    default_end = process_statements(stmt.default_body, default_block, break_target=switch_merge, continue_target=continue_target)
                    default_end.add_successor(switch_merge)
                current = switch_merge
            elif isinstance(stmt, ReturnStatement):
                current.add_successor(cfg.exit)
                return cfg.exit
            elif isinstance(stmt, BreakStatement):
                if break_target:
                    current.add_successor(break_target)
                return break_target or cfg.exit
            elif isinstance(stmt, ContinueStatement):
                if continue_target:
                    current.add_successor(continue_target)
                return continue_target or cfg.exit
            else:
                current.statements.append(stmt)
        return current

    if isinstance(func_node, Module):
        final_block = process_statements(func_node.body, entry)
    elif isinstance(func_node, (FunctionDeclaration, MethodDeclaration)):
        final_block = process_statements(func_node.body, entry)
    if final_block and final_block != cfg.exit:
        final_block.add_successor(cfg.exit)
    cfg.compute_dominators()
    return cfg
