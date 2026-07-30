#!/usr/bin/env python3
"""Evidence — Objek terstruktur untuk bukti audit."""
from dataclasses import dataclass, field
from typing import Optional, Any

@dataclass
class Evidence:
    """Bukti audit yang terstruktur, bukan string mentah."""
    line: Optional[int] = None
    column: Optional[int] = None
    snippet: str = ""
    node_type: str = ""           # Nama kelas node AST
    node: Any = None              # Referensi node AST (opsional)
    confidence: str = "MEDIUM"    # HIGH / MEDIUM / LOW
    message: str = ""
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            'line': self.line,
            'column': self.column,
            'snippet': self.snippet,
            'node_type': self.node_type,
            'confidence': self.confidence,
            'message': self.message,
            'suggestion': self.suggestion,
        }

    def to_line_string(self) -> str:
        if self.line:
            return f"Line {self.line}: {self.snippet[:50]}"
        return f"{self.node_type}: {self.snippet[:50]}"

    @classmethod
    def from_regex(cls, line: int, snippet: str, confidence: str = "MEDIUM") -> 'Evidence':
        return cls(line=line, snippet=snippet, confidence=confidence)

    @classmethod
    def from_ast(cls, node: Any, message: str, confidence: str = "HIGH") -> 'Evidence':
        node_type = type(node).__name__ if node else ""
        line = getattr(node, 'line', None) if hasattr(node, 'line') else None
        col = getattr(node, 'col', None) if hasattr(node, 'col') else None
        return cls(line=line, column=col, node_type=node_type, node=node,
                   confidence=confidence, message=message)
