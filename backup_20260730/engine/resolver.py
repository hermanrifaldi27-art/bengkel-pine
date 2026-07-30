import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

class ParameterResolver:
    def __init__(self, context: Dict[str, Any]):
        self.context = context  # berisi AST, symbols, constants, dll.
        self.resolvers = {
            "var": self._resolve_var,
            "limit": self._resolve_limit,
            # "box": self._resolve_box,
            # "line": self._resolve_line,
        }
    
    def resolve(self, rule: Dict) -> Optional[Dict[str, Any]]:
        params = rule.get('parameters', [])
        if not params:
            return {}
        
        result = {}
        for p in params:
            name = p.get('name')
            required = p.get('required', False)
            if not name:
                continue
            
            resolver = self.resolvers.get(name)
            if resolver:
                value = resolver(p)
                if value is not None:
                    result[name] = value
                elif required:
                    logger.warning(f"Parameter wajib '{name}' gagal resolve di rule {rule.get('id')}")
                    return None
                else:
                    result[name] = None
            else:
                logger.warning(f"Parameter '{name}' tidak dikenal (harus didaftarkan di registry)")
                if required:
                    return None
                result[name] = None
        return result if 'var' in result else None
    
    def _resolve_var(self, param: Dict) -> Optional[str]:
        symbols = self.context.get('symbols', {})
        # Prioritaskan array/matrix terakhir yang muncul
        arrays = self.context.get('arrays', [])
        if arrays:
            return arrays[-1]
        matrices = self.context.get('matrices', [])
        if matrices:
            return matrices[-1]
        # Fallback ke symbol var biasa
        for name, typ in symbols.items():
            if typ in ("array", "matrix"):
                return name
        return None
    
    def _resolve_limit(self, param: Dict) -> Optional[int]:
        constants = self.context.get('constants', {})
        default = param.get('default', 100)
        # Cari konstanta yang cocok
        for name, val in constants.items():
            if any(k in name.lower() for k in ['max', 'limit', 'memory', 'depth', 'batch', 'size', 'buffer']):
                return val
        return default
