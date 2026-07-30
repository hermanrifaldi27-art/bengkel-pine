#!/usr/bin/env python3
"""
Pine Type System v6 — FINAL MASTER (frozen-safe)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Any, Union, Set
from enum import Enum

class Qualifier(Enum):
    LITERAL = "literal"
    CONST = "const"
    INPUT = "input"
    SIMPLE = "simple"
    SERIES = "series"

    @classmethod
    def combine(cls, *qualifiers: 'Qualifier') -> 'Qualifier':
        order = [cls.LITERAL, cls.CONST, cls.INPUT, cls.SIMPLE, cls.SERIES]
        return max(qualifiers, key=lambda q: order.index(q))

    def is_stronger_than(self, other: 'Qualifier') -> bool:
        order = [Qualifier.LITERAL, Qualifier.CONST, Qualifier.INPUT, Qualifier.SIMPLE, Qualifier.SERIES]
        return order.index(self) > order.index(other)

class TypeKind(Enum):
    NA = "na"
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    COLOR = "color"
    ARRAY = "array"
    MATRIX = "matrix"
    MAP = "map"
    TUPLE = "tuple"
    LINE = "line"
    LINEFILL = "linefill"
    BOX = "box"
    LABEL = "label"
    TABLE = "table"
    POLYLINE = "polyline"
    HLINE = "hline"
    FUNCTION = "function"
    VOID = "void"
    DYNAMIC = "dynamic"
    ENUM = "enum"

@dataclass(frozen=True)
class PineType:
    kind: TypeKind = TypeKind.VOID
    qualifier: Qualifier = Qualifier.SERIES
    element_type: Optional['PineType'] = None
    key_type: Optional['PineType'] = None

    @property
    def is_series(self) -> bool:
        return self.qualifier == Qualifier.SERIES
    @property
    def is_const(self) -> bool:
        return self.qualifier in (Qualifier.LITERAL, Qualifier.CONST)

    def with_qualifier(self, qualifier: Qualifier) -> 'PineType':
        return PineType(self.kind, qualifier, self.element_type, self.key_type)
    def as_series(self) -> 'PineType':
        return self.with_qualifier(Qualifier.SERIES)
    def propagate(self, *others: 'PineType') -> 'PineType':
        strongest = self.qualifier
        for o in others:
            strongest = Qualifier.combine(strongest, o.qualifier)
        return self.with_qualifier(strongest)

    def __repr__(self) -> str:
        q = f"{self.qualifier.value} " if self.qualifier != Qualifier.SERIES else ""
        if self.kind == TypeKind.MAP and self.key_type and self.element_type:
            return f"{q}map<{self.key_type}, {self.element_type}>"
        if self.kind in (TypeKind.ARRAY, TypeKind.MATRIX) and self.element_type:
            return f"{q}{self.kind.value}<{self.element_type}>"
        return f"{q}{self.kind.value}"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PineType): return False
        return (self.kind == other.kind and self.qualifier == other.qualifier and
                self.element_type == other.element_type and self.key_type == other.key_type)
    def __hash__(self) -> int:
        return hash((self.kind, self.qualifier, self.element_type, self.key_type))

    @staticmethod
    def from_ast(node) -> Optional['PineType']:
        from engine.parser import Identifier, GenericType
        if isinstance(node, Identifier):
            kind_map = {
                'int': TypeKind.INT, 'float': TypeKind.FLOAT, 'bool': TypeKind.BOOL,
                'string': TypeKind.STRING, 'color': TypeKind.COLOR,
                'line': TypeKind.LINE, 'linefill': TypeKind.LINEFILL,
                'box': TypeKind.BOX, 'label': TypeKind.LABEL,
                'table': TypeKind.TABLE, 'hline': TypeKind.HLINE,
                'polyline': TypeKind.POLYLINE, 'void': TypeKind.VOID,
            }
            if node.name in kind_map:
                return PineType(kind_map[node.name], Qualifier.CONST)
        elif isinstance(node, GenericType):
            base_map = {'array': TypeKind.ARRAY, 'matrix': TypeKind.MATRIX, 'map': TypeKind.MAP}
            if node.base in base_map and node.params:
                if node.base == 'map' and len(node.params) >= 2:
                    return PineType(TypeKind.MAP, Qualifier.SERIES,
                                    PineType.from_ast(node.params[1]),
                                    PineType.from_ast(node.params[0]))
                return PineType(base_map[node.base], Qualifier.SERIES,
                                PineType.from_ast(node.params[0]))
        return None

    @staticmethod
    def infer_from_value(value: Any) -> Optional['PineType']:
        if isinstance(value, bool): return PineType(TypeKind.BOOL, Qualifier.LITERAL)
        if isinstance(value, int): return PineType(TypeKind.INT, Qualifier.LITERAL)
        if isinstance(value, float): return PineType(TypeKind.FLOAT, Qualifier.LITERAL)
        if isinstance(value, str): return PineType(TypeKind.STRING, Qualifier.LITERAL)
        return None

@dataclass(frozen=True)
class EnumType(PineType):
    enum_name: str = ""
    allowed_values: Set[str] = field(default_factory=set)
    def __repr__(self) -> str: return f"enum[{self.enum_name}]"
    def validate(self, full_value_name: str) -> bool: return full_value_name in self.allowed_values

def _enum(name: str, *values: str) -> EnumType:
    return EnumType(enum_name=name, allowed_values={f"{name}.{v}" for v in values})

ENUM_DISPLAY        = _enum("display", "all","none","status_line","pane","data_window")
ENUM_BARMERGE_GAPS  = _enum("barmerge.gaps", "off","on")
ENUM_BARMERGE_LOOK  = _enum("barmerge.lookahead", "off","on")
ENUM_XLOC           = _enum("xloc", "bar_index","bar_time")
ENUM_YLOC           = _enum("yloc", "price","pane","bottom","top")
ENUM_SIZE           = _enum("size", "auto","tiny","small","normal","large","huge")
ENUM_PLOT_STYLE     = _enum("plot.style", "line","linebr","stepline","stepline_diamond","area","columns","histogram","cross","circles")
ENUM_PLOT_LINESTYLE = _enum("plot.linestyle", "solid","dashed","dotted")
ENUM_SHAPE          = _enum("shape", "circle","triangleup","triangledown","labelup","labeldown","xcross","arrowup","arrowdown","diamond","square")
ENUM_LOCATION       = _enum("location", "abovebar","belowbar","absolute")
ENUM_EXTEND         = _enum("extend", "none","left","right","both")
ENUM_LABEL_STYLE    = _enum("label.style", "none","arrow_up","arrow_down","label_up","label_down","label_left","label_right")
ENUM_TEXT_ALIGN     = _enum("text.align", "left","center","right")
ENUM_SCALE          = _enum("scale", "left","right","none")
ENUM_CURRENCY       = _enum("currency", "USD","EUR","GBP","JPY","CAD","CHF","AUD","CNY","HKD","SGD","SEK","KRW","NZD","INR","RUB","TRY","NONE")
ENUM_ALERT_FREQ     = _enum("alert.freq", "once_per_bar_close","once_per_bar","once_per_close","all")
ENUM_POSITION       = _enum("position", "top_left","top_center","top_right","middle_left","middle_center","middle_right","bottom_left","bottom_center","bottom_right")

TYPE_NA      = PineType(TypeKind.NA, Qualifier.CONST)
def _make_na(): return TYPE_NA
TYPE_BOOL    = PineType(TypeKind.BOOL, Qualifier.SIMPLE)
TYPE_INT     = PineType(TypeKind.INT, Qualifier.SIMPLE)
TYPE_FLOAT   = PineType(TypeKind.FLOAT, Qualifier.SIMPLE)
TYPE_STRING  = PineType(TypeKind.STRING, Qualifier.SIMPLE)
TYPE_COLOR   = PineType(TypeKind.COLOR, Qualifier.SIMPLE)
TYPE_VOID    = PineType(TypeKind.VOID, Qualifier.CONST)

TYPE_SERIES_BOOL   = TYPE_BOOL.as_series()
TYPE_SERIES_INT    = TYPE_INT.as_series()
TYPE_SERIES_FLOAT  = TYPE_FLOAT.as_series()
TYPE_SERIES_STRING = TYPE_STRING.as_series()

TYPE_INPUT_BOOL   = TYPE_BOOL.with_qualifier(Qualifier.INPUT)
TYPE_INPUT_INT    = TYPE_INT.with_qualifier(Qualifier.INPUT)
TYPE_INPUT_FLOAT  = TYPE_FLOAT.with_qualifier(Qualifier.INPUT)
TYPE_INPUT_STRING = TYPE_STRING.with_qualifier(Qualifier.INPUT)
TYPE_INPUT_COLOR  = TYPE_COLOR.with_qualifier(Qualifier.INPUT)

TYPE_LINE     = PineType(TypeKind.LINE, Qualifier.SERIES)
TYPE_LINEFILL = PineType(TypeKind.LINEFILL, Qualifier.SERIES)
TYPE_BOX      = PineType(TypeKind.BOX, Qualifier.SERIES)
TYPE_LABEL    = PineType(TypeKind.LABEL, Qualifier.SERIES)
TYPE_TABLE    = PineType(TypeKind.TABLE, Qualifier.SERIES)
TYPE_POLYLINE = PineType(TypeKind.POLYLINE, Qualifier.SERIES)
TYPE_HLINE    = PineType(TypeKind.HLINE, Qualifier.SERIES)

@dataclass(frozen=True)
class TupleType(PineType):
    element_types: List[PineType] = field(default_factory=list)
    element_names: Optional[List[str]] = None
    def __post_init__(self):
        if self.element_types:
            strongest = Qualifier.combine(*(t.qualifier for t in self.element_types))
            object.__setattr__(self, 'qualifier', strongest)

@dataclass(frozen=True)
class ArrayType(PineType):
    element_type: PineType = field(default_factory=_make_na)

@dataclass(frozen=True)
class MatrixType(PineType):
    element_type: PineType = field(default_factory=_make_na)

@dataclass(frozen=True)
class MapType(PineType):
    key_type: PineType = field(default_factory=_make_na)
    element_type: PineType = field(default_factory=_make_na)

@dataclass(frozen=True)
class DynamicType(PineType):
    param_index: int = 0
    take_qualifier: bool = True
    def resolve(self, arg_types: List[PineType]) -> PineType:
        if self.param_index < len(arg_types):
            t = arg_types[self.param_index]
            return t if self.take_qualifier else t.with_qualifier(Qualifier.SERIES)
        return TYPE_NA

TYPE_DYNAMIC_EXPR = DynamicType(0)

@dataclass
class Parameter:
    name: str
    type: Union[PineType, DynamicType]
    optional: bool = False
    default: Any = None

@dataclass
class Signature:
    params: List[Parameter]
    return_type: Union[PineType, DynamicType, TupleType]
    min_params: int = field(init=False)
    def __post_init__(self):
        self.min_params = sum(1 for p in self.params if not p.optional)

class OverloadResolver:
    @staticmethod
    def resolve(overloads: List[Signature], arg_types: List[PineType]) -> Optional[Signature]:
        best_match, best_score = None, -1
        for sig in overloads:
            score = OverloadResolver._match(sig, arg_types)
            if score > best_score:
                best_score, best_match = score, sig
        return best_match if best_score >= 0 else None

    @staticmethod
    def _match(sig: Signature, arg_types: List[PineType]) -> int:
        argc = len(arg_types)
        if argc < sig.min_params or argc > len(sig.params): return -1
        score = 0
        for i, arg_t in enumerate(arg_types):
            param_t = sig.params[i].type
            if isinstance(param_t, DynamicType):
                score += 8; continue
            if isinstance(param_t, EnumType):
                if isinstance(arg_t, EnumType) and arg_t.enum_name == param_t.enum_name: score += 15
                elif arg_t.kind == TypeKind.STRING and arg_t.is_const: score += 10
                else: return -1
                continue
            if param_t.kind == arg_t.kind:
                score += 10
                if arg_t.qualifier.is_stronger_than(param_t.qualifier) or arg_t.qualifier == param_t.qualifier:
                    score += 3
                else: return -1
            else: return -1
        return score
