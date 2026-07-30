#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/sdcard/bengkel-pine')
import unittest
from engine.parser import PineAST
from engine.matcher import RuleMatcher
from engine.resolver import ParameterResolver
from engine.patch import PatchExecutor
from engine.verify import VerificationEngine

class TestParser(unittest.TestCase):
    def test_parse_array(self):
        code = 'var myArray = array.new<float>()'
        ast = PineAST(code)
        self.assertIn('myArray', ast.get_arrays())
    
    def test_parse_matrix(self):
        code = 'var matrix<float> m = matrix.new<float>(0, 9)'
        ast = PineAST(code)
        self.assertIn('m', ast.get_matrices())
    
    def test_parse_constants(self):
        code = 'const MAX = 100'
        ast = PineAST(code)
        self.assertEqual(ast.get_constants().get('MAX'), 100)

class TestResolver(unittest.TestCase):
    def test_resolve_without_params(self):
        context = {'arrays': ['myArray']}
        resolver = ParameterResolver(context)
        resolved = resolver.resolve({'parameters': []})
        self.assertEqual(resolved, {})
    
    def test_resolve_var(self):
        context = {'arrays': ['myArray']}
        resolver = ParameterResolver(context)
        resolved = resolver.resolve({'parameters': [{'name': 'var'}]})
        self.assertEqual(resolved.get('var'), 'myArray')

class TestPatch(unittest.TestCase):
    def test_inject_after(self):
        code = 'array.push(arr, 1)'
        patcher = PatchExecutor(code)
        result = patcher.apply(
            {'action': {'operation': 'inject_after', 'anchor': 'array.push(arr', 'template': 'while true'}},
            {'var': 'arr'}
        )
        self.assertIn('while true', result)
    
    def test_remove_keyword(self):
        code = 'return close'
        patcher = PatchExecutor(code)
        result = patcher.apply(
            {'action': {'operation': 'remove_keyword', 'anchor': 'return'}},
            {}
        )
        self.assertNotIn('return', result)

if __name__ == '__main__':
    unittest.main()
