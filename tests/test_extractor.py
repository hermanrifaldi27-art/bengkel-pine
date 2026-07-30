#!/usr/bin/env python3
"""Unit Test untuk Extractor"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.parser import PineAST
from engine.extractor import FeatureExtractor

def test_var_int_na():
    """Test deteksi var int = na"""
    code = '''//@version=6
indicator("Test")
var int x = na
plot(close)
'''
    ast = PineAST(code)
    extractor = FeatureExtractor(ast.root, code)
    features = extractor.extract_all()
    
    var_na = [f for f in features if f.detector_id == 'var_int_na_v1']
    assert len(var_na) == 1, f"Harusnya 1 var_int_na, dapat {len(var_na)}"
    print("✅ test_var_int_na LULUS")

def test_plot_in_if():
    """Test deteksi plot di dalam if global"""
    code = '''//@version=6
indicator("Test")
if close > open
    plot(close)
'''
    ast = PineAST(code)
    extractor = FeatureExtractor(ast.root, code)
    features = extractor.extract_all()
    
    plot_if = [f for f in features if 'plot_in_if' in f.detector_id]
    assert len(plot_if) == 1, f"Harusnya 1 plot_in_if, dapat {len(plot_if)}"
    print("✅ test_plot_in_if LULUS")

def test_request_security_lookahead():
    """Test deteksi request.security tanpa lookahead"""
    code = '''//@version=6
indicator("Test")
x = request.security("AAPL", "D", close)
plot(x)
'''
    ast = PineAST(code)
    extractor = FeatureExtractor(ast.root, code)
    features = extractor.extract_all()
    
    req = [f for f in features if 'request_security_lookahead' in f.detector_id]
    assert len(req) == 1, f"Harusnya 1 request_security, dapat {len(req)}"
    print("✅ test_request_security_lookahead LULUS")

def test_no_false_positive():
    """Test tidak ada false positive untuk kode bersih"""
    code = '''//@version=6
indicator("Test")
var int x = 0
plot(close)
x := request.security("AAPL", "D", close, lookahead = barmerge.lookahead_off)
'''
    ast = PineAST(code)
    extractor = FeatureExtractor(ast.root, code)
    features = extractor.extract_all()
    
    assert len(features) == 0, f"Harusnya 0 masalah, dapat {len(features)}"
    print("✅ test_no_false_positive LULUS")

if __name__ == "__main__":
    test_var_int_na()
    test_plot_in_if()
    test_request_security_lookahead()
    test_no_false_positive()
    print("\n🎉 Semua test LULUS!")
