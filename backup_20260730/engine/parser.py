import re
from typing import Dict, List, Any

class PineAST:
    """Representasi AST sederhana untuk Pine Script"""
    def __init__(self, code: str):
        self.code = code
        self.symbols = {}   # nama → tipe (var, array, matrix, const)
        self.arrays = []
        self.matrices = []
        self.constants = {}
        self.functions = []
        self._parse()
    
    def _parse(self):
        # Ekstrak var array/matrix
        for match in re.finditer(r'var\s+(\w+)\s*=\s*array\.new', self.code):
            self.symbols[match.group(1)] = "array"
            self.arrays.append(match.group(1))
        for match in re.finditer(r'var\s+(\w+)\s*=\s*matrix\.new', self.code):
            self.symbols[match.group(1)] = "matrix"
            self.matrices.append(match.group(1))
        # Ekstrak konstanta
        for match in re.finditer(r'(?:const\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(\d+)', self.code):
            self.constants[match.group(1)] = int(match.group(2))
        # Ekstrak fungsi
        for match in re.finditer(r'(\w+)\s*\([^)]*\)\s*=>', self.code):
            self.functions.append(match.group(1))
    
    def get_symbols(self):
        return self.symbols
    
    def get_constants(self):
        return self.constants
    
    def get_arrays(self):
        return self.arrays
    
    def get_matrices(self):
        return self.matrices
