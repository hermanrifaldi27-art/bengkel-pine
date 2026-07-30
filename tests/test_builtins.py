#!/usr/bin/env python3
"""Unit Test untuk Builtin Registry"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pine_builtins import BuiltinRegistry

def test_namespace_count():
    """Test jumlah namespace"""
    registry = BuiltinRegistry()
    assert len(registry.namespaces) >= 30, f"Minimal 30 namespace, dapat {len(registry.namespaces)}"
    print(f"✅ test_namespace_count LULUS ({len(registry.namespaces)} namespace)")

def test_resolve_global():
    """Test resolve variabel global"""
    registry = BuiltinRegistry()
    val = registry.resolve(['close'])
    assert val is not None, "close harusnya ada"
    print(f"✅ test_resolve_global LULUS (close = {val.type})")

def test_resolve_namespace():
    """Test resolve namespace bertingkat"""
    registry = BuiltinRegistry()
    val = registry.resolve(['ta', 'sma'])
    assert val is not None, "ta.sma harusnya ada"
    print(f"✅ test_resolve_namespace LULUS (ta.sma)")

    val = registry.resolve(['strategy', 'risk', 'max_drawdown'])
    assert val is not None, "strategy.risk.max_drawdown harusnya ada"
    print(f"✅ test_resolve_namespace LULUS (strategy.risk.max_drawdown)")

def test_global_functions():
    """Test fungsi global"""
    registry = BuiltinRegistry()
    assert 'indicator' in registry.global_functions, "indicator harusnya ada"
    assert 'plot' in registry.global_functions, "plot harusnya ada"
    assert 'strategy' in registry.global_functions, "strategy harusnya ada"
    print(f"✅ test_global_functions LULUS ({len(registry.global_functions)} fungsi)")

if __name__ == "__main__":
    test_namespace_count()
    test_resolve_global()
    test_resolve_namespace()
    test_global_functions()
    print("\n🎉 Semua test LULUS!")
