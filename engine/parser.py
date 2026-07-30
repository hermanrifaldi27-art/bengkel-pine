import re
from typing import Dict, List, Any

class PineAST:
    def __init__(self, code: str):
        self.code = code
        self.symbols: Dict[str, str] = {}
        self.arrays: List[str] = []
        self.matrices: List[str] = []
        self.constants: Dict[str, int] = {}
        self.functions: List[str] = []
        self._parse()
    
    def _parse(self):
        patterns_array = [
            r'var\s+(?:\w+\s+)?(\w+)\s*=\s*array\.new',
            r'var\s+array(?:<\w+>)?\s+(\w+)\s*=',
            r'(\w+)\s*=\s*array\.new(?:<\w+>)?\s*\(',
        ]
        for pat in patterns_array:
            for match in re.finditer(pat, self.code):
                name = match.group(1)
                if name not in self.arrays:
                    self.symbols[name] = "array"
                    self.arrays.append(name)
        
        patterns_matrix = [
            r'var\s+(?:\w+\s+)?(\w+)\s*=\s*matrix\.new',
            r'var\s+matrix(?:<\w+>)?\s+(\w+)\s*=',
            r'(\w+)\s*=\s*matrix\.new(?:<\w+>)?\s*\(',
        ]
        for pat in patterns_matrix:
            for match in re.finditer(pat, self.code):
                name = match.group(1)
                if name not in self.matrices:
                    self.symbols[name] = "matrix"
                    self.matrices.append(name)
        
        for match in re.finditer(r'(?:const\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\d+)\b', self.code):
            name = match.group(1)
            if name not in self.symbols:
                self.constants[name] = int(match.group(2))
                if name.isupper() or any(k in name.lower() for k in ['max', 'limit', 'memory', 'depth', 'size']):
                    self.symbols[name] = "const"
        
        for match in re.finditer(r'(?:method\s+)?(\w+)\s*\([^)]*\)\s*=>', self.code):
            self.functions.append(match.group(1))
    
    def get_symbols(self) -> Dict[str, str]:
        return self.symbols
    
    def get_constants(self) -> Dict[str, int]:
        return self.constants
    
    def get_arrays(self) -> List[str]:
        return self.arrays
    
    def get_matrices(self) -> List[str]:
        return self.matrices
