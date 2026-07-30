import re
import hashlib

class SignatureGenerator:
    @staticmethod
    def normalize(block: str) -> str:
        """Normalisasi kode untuk hash yang stabil"""
        # Hapus komentar
        block = re.sub(r'//.*', '', block)
        block = re.sub(r'/\*.*?\*/', '', block, flags=re.DOTALL)
        
        # Ganti nama variabel dengan {var}
        keywords = ['if', 'else', 'for', 'while', 'var', 'na', 'true', 'false', 'in', 
                   'array', 'map', 'matrix', 'method', 'plot', 'label', 'line', 'box', 
                   'table', 'ta', 'math', 'str', 'request']
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        
        def replace(match):
            w = match.group(1)
            if w in keywords or w.startswith('f_') or w in ['len', 'src', 'atr', 'osc', 
                                                            'close', 'high', 'low', 'open']:
                return w
            return '{var}'
        block = re.sub(pattern, replace, block)
        
        # Ganti angka literal (kecuali 0,1,2)
        block = re.sub(r'\b[3-9][0-9]*\b', '{num}', block)
        
        # Hilangkan spasi berlebih
        return re.sub(r'\s+', ' ', block).strip()
    
    @staticmethod
    def generate(block: str) -> str:
        """Generate 8-char signature dari blok kode"""
        normalized = SignatureGenerator.normalize(block)
        return hashlib.sha256(normalized.encode()).hexdigest()[:8]
