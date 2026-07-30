import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ParameterResolver:
    def __init__(self, context: Dict[str, Any]):
        self.context = context
        self.resolvers = {
            "var": self._resolve_var,
            "limit": self._resolve_limit,
            "pivot_func": self._resolve_pivot_func,
            "neighbors_var": self._resolve_var,
            "cols": self._resolve_cols,
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
                    result[name] = p.get('default')
            else:
                logger.warning(f"Parameter '{name}' tidak dikenal")
                if required:
                    return None
                result[name] = p.get('default')
        
        # 🔥 FIX: Jangan hard-require 'var'
        return result
    
    def _resolve_var(self, param: Dict) -> Optional[str]:
        arrays = self.context.get('arrays', [])
        if arrays:
            return arrays[-1]
        matrices = self.context.get('matrices', [])
        if matrices:
            return matrices[-1]
        symbols = self.context.get('symbols', {})
        for name, typ in symbols.items():
            if typ in ("array", "matrix"):
                return name
        return None
    
    def _resolve_limit(self, param: Dict) -> Optional[int]:
        constants = self.context.get('constants', {})
        default = param.get('default', 100)
        for name, val in constants.items():
            if any(k in name.lower() for k in ['max', 'limit', 'memory', 'depth', 'batch', 'size', 'buffer']):
                return val
        return default
    
    def _resolve_pivot_func(self, param: Dict) -> Optional[str]:
        code = self.context.get('ast').code if self.context.get('ast') else ""
        if 'ta.pivothigh' in code:
            return 'ta.pivothigh'
        if 'ta.pivotlow' in code:
            return 'ta.pivotlow'
        return None
    
    def _resolve_cols(self, param: Dict) -> Optional[int]:
        return param.get('default', 9)
