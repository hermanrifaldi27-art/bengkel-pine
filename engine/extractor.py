#!/usr/bin/env python3
import re
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class Feature:
    module: str
    goal: str
    tactic: str
    context: str
    signature: str
    detector_id: str
    anchor: Optional[str] = None

class FeatureExtractor:
    def __init__(self, ast):
        self.ast = ast
        self.code = ast.code
        self.features = []
    
    def extract_all(self) -> List[Feature]:
        # Array unbounded → cleanup.fifo.shift
        self._detect_array_unbounded()
        # Matrix unbounded → cleanup.matrix.remove_row
        self._detect_matrix_unbounded()
        # var int = na → state.fix_int_na
        self._detect_var_int_na()
        # return in function → functions.no_return
        self._detect_return_in_function()
        # plot in if → plots.plot_in_if
        self._detect_plot_in_if()
        # alertcondition in if → alert.alertcondition_in_if
        self._detect_alertcondition_in_if()
        # request.security tanpa lookahead_off → data_fetching.lookahead
        self._detect_request_security_lookahead()
        return self.features
    
    def _add_feature(self, module: str, goal: str, tactic: str, context: str, detector_id: str, anchor: str = None):
        from engine.signature import SignatureGenerator
        sig = SignatureGenerator.generate(tactic)
        self.features.append(Feature(
            module=module,
            goal=goal,
            tactic=tactic,
            context=context,
            signature=sig,
            detector_id=detector_id,
            anchor=anchor
        ))
    
    # ── Detectors ──
    def _detect_array_unbounded(self):
        code = self.code
        if 'array.push' in code and 'array.new' in code:
            has_eviction = bool(re.search(r'while\s+array\.size|array\.shift|array\.pop|array\.remove', code))
            if not has_eviction:
                self._add_feature(
                    'cleanup',
                    'Array unbounded — tambahkan eviction (while + shift)',
                    'while array.size({var}) > {limit}\n    array.shift({var})',
                    'CALCULATIONS',
                    'array_unbounded_v1',
                    anchor='array.push({var}'
                )
    
    def _detect_matrix_unbounded(self):
        code = self.code
        if 'matrix.add_row' in code and 'matrix.new' in code:
            has_eviction = bool(re.search(r'matrix\.remove_row', code))
            if not has_eviction:
                self._add_feature(
                    'cleanup',
                    'Matrix unbounded — tambahkan eviction (remove_row)',
                    'if matrix.rows({var}) > {limit}\n    matrix.remove_row({var}, matrix.rows({var}) - 1)',
                    'CALCULATIONS',
                    'matrix_unbounded_v1',
                    anchor='matrix.add_row({var}'
                )
    
    def _detect_var_int_na(self):
        code = self.code
        if re.search(r'var\s+int\s+.*?=\s*na', code):
            self._add_feature(
                'state',
                'var int = na → ubah menjadi 0',
                'var int {var} = 0',
                'STATE',
                'var_int_na_v1'
            )
    
    def _detect_return_in_function(self):
        code = self.code
        if re.search(r'(?:method\s+)?\w+\s*\([^)]*\)\s*=>\s*\{.*?return', code, re.DOTALL):
            self._add_feature(
                'functions',
                'return di dalam fungsi → hapus',
                '',
                'FUNCTIONS',
                'return_in_function_v1',
                anchor='return'
            )
    
    def _detect_plot_in_if(self):
        code = self.code
        if re.search(r'if\s+[^:\n]*:\s*\n\s*plot\s*\(', code):
            self._add_feature(
                'plots',
                'plot di dalam if → pindahkan ke global scope',
                'plot({cond} ? {expr} : na)',
                'PLOTS',
                'plot_in_if_v1',
                anchor='plot('
            )
    
    def _detect_alertcondition_in_if(self):
        code = self.code
        if re.search(r'if\s+[^:\n]*:\s*\n\s*alertcondition\s*\(', code):
            self._add_feature(
                'alert',
                'alertcondition di dalam if → pindahkan ke global scope',
                'alertcondition(...)',
                'ALERT',
                'alertcondition_in_if_v1',
                anchor='alertcondition('
            )
    
    def _detect_request_security_lookahead(self):
        code = self.code
        if 'request.security' in code and 'lookahead_off' not in code:
            self._add_feature(
                'data_fetching',
                'request.security tanpa lookahead_off → tambahkan',
                'request.security(..., lookahead = barmerge.lookahead_off)',
                'DATA_FETCHING',
                'request_security_lookahead_v1',
                anchor='request.security('
            )

def extract_features(file_path: str):
    from engine.parser import PineAST
    from engine.contract_writer import ContractWriter
    print(f"🔍 Ekstraksi {file_path}...")
    with open(file_path, 'r') as f:
        code = f.read()
    ast = PineAST(code)
    extractor = FeatureExtractor(ast)
    features = extractor.extract_all()
    if not features:
        print("   ℹ️ Tidak ada pola ditemukan.")
        return
    print(f"   📊 Ditemukan {len(features)} fitur:")
    for f in features:
        print(f"   - {f.module}: {f.goal} ({f.signature})")
        ContractWriter.write_rule(f, dry_run=False)
    print("✅ Ekstraksi selesai.")
