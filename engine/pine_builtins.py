#!/usr/bin/env python3
"""
Pine Script v6 Builtins — FINAL MASTER 100%
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
from engine.types import (
    PineType, Qualifier, TypeKind,
    TYPE_NA, TYPE_INT, TYPE_FLOAT, TYPE_BOOL, TYPE_STRING, TYPE_COLOR,
    TYPE_LINE, TYPE_LINEFILL, TYPE_BOX, TYPE_LABEL, TYPE_TABLE,
    TYPE_POLYLINE, TYPE_HLINE, TYPE_VOID,
    TYPE_SERIES_INT, TYPE_SERIES_FLOAT, TYPE_SERIES_BOOL, TYPE_SERIES_STRING,
    TYPE_INPUT_INT, TYPE_INPUT_FLOAT, TYPE_INPUT_BOOL, TYPE_INPUT_STRING, TYPE_INPUT_COLOR,
    TupleType, ArrayType, MatrixType, MapType, DynamicType, TYPE_DYNAMIC_EXPR,
    EnumType, ENUM_DISPLAY, ENUM_BARMERGE_GAPS, ENUM_BARMERGE_LOOK,
    ENUM_XLOC, ENUM_YLOC, ENUM_SIZE, ENUM_PLOT_STYLE, ENUM_PLOT_LINESTYLE,
    ENUM_SHAPE, ENUM_LOCATION, ENUM_EXTEND, ENUM_LABEL_STYLE, ENUM_TEXT_ALIGN,
    ENUM_SCALE, ENUM_CURRENCY, ENUM_ALERT_FREQ, ENUM_POSITION,
    Signature, Parameter
)

class BuiltinValue: pass

@dataclass
class ConstantValue(BuiltinValue):
    value: Any
    type: PineType

@dataclass
class BuiltinFunction(BuiltinValue):
    name: str
    overloads: List[Signature] = field(default_factory=list)

class Namespace:
    def __init__(self, name: str):
        self.name = name
        self.members: Dict[str, Any] = {}
    def add_const(self, name: str, value: Any, type_: PineType):
        self.members[name] = ConstantValue(value, type_)
    def add_func(self, name: str, signature: Signature):
        fn = self.members.get(name)
        if not isinstance(fn, BuiltinFunction):
            fn = BuiltinFunction(name)
            self.members[name] = fn
        fn.overloads.append(signature)
    def add_subns(self, name: str) -> 'Namespace':
        ns = Namespace(name)
        self.members[name] = ns
        return ns
    def get(self, member: str):
        return self.members.get(member)

class BuiltinRegistry:
    def __init__(self):
        self.namespaces: Dict[str, Namespace] = {}
        self.global_series: Dict[str, ConstantValue] = {}
        self.global_functions: Dict[str, BuiltinFunction] = {}
        self._init_all()

    def resolve(self, parts):
        if not parts: return None
        if len(parts) == 1:
            return self.global_series.get(parts[0]) or self.global_functions.get(parts[0])
        current = self.namespaces.get(parts[0])
        if not current: return None
        for part in parts[1:]:
            val = current.members.get(part)
            if val is None: return None
            if isinstance(val, Namespace): current = val
            else: return val
        return None

    def _init_all(self):
        self._init_enum_namespaces()
        self._init_global_funcs()
        self._init_color()
        self._init_barmerge()
        self._init_display_xloc_yloc_size_scale()
        self._init_plot_alert_consts()
        self._init_drawing_objects()
        self._init_font_session_location()
        self._init_timeframe()
        self._init_syminfo()
        self._init_barstate()
        self._init_ta()
        self._init_math()
        self._init_str()
        self._init_input()
        self._init_request()
        self._init_collections()
        self._init_strategy()
        self._init_chart()
        self._init_linefill()
        self._init_log()
        self._init_global_series()

    def _init_enum_namespaces(self):
        # shape, extend, scale, text
        for ns_name, enum_type in [('shape', ENUM_SHAPE), ('extend', ENUM_EXTEND), ('scale', ENUM_SCALE)]:
            ns = Namespace(ns_name)
            for v in enum_type.allowed_values:
                short = v.split('.')[-1]
                ns.add_const(short, v, enum_type)
            self.namespaces[ns_name] = ns
        # text
        ns = Namespace('text')
        for v in ENUM_TEXT_ALIGN.allowed_values:
            short = v.split('.')[-1]
            ns.add_const(f'align_{short}', v, ENUM_TEXT_ALIGN)
        self.namespaces['text'] = ns
        # hline
        ns = Namespace('hline')
        for v in ENUM_PLOT_LINESTYLE.allowed_values:
            short = v.split('.')[-1]
            ns.add_const(f'style_{short}', v, ENUM_PLOT_LINESTYLE)
        self.namespaces['hline'] = ns
        # order
        ns = Namespace('order')
        for o in ['none','long','short','all']:
            ns.add_const(o, f'order.{o}', TYPE_STRING)
        self.namespaces['order'] = ns
        # dayofweek
        ns = Namespace('dayofweek')
        for i, d in enumerate(['sunday','monday','tuesday','wednesday','thursday','friday','saturday']):
            ns.add_const(d, f'dayofweek.{d}', TYPE_INT)
        self.namespaces['dayofweek'] = ns
        # adjustment
        ns = Namespace('adjustment')
        for a in ['splits','dividends','all','none']:
            ns.add_const(a, f'adjustment.{a}', TYPE_STRING)
        self.namespaces['adjustment'] = ns
        # backadjustment
        ns = Namespace('backadjustment')
        ns.add_const('all', 'backadjustment.all', TYPE_STRING)
        ns.add_const('none', 'backadjustment.none', TYPE_STRING)
        self.namespaces['backadjustment'] = ns
        # dividends
        ns = Namespace('dividends')
        for d in ['amount','yield','date']:
            ns.add_const(d, f'dividends.{d}', TYPE_STRING)
        self.namespaces['dividends'] = ns
        # earnings
        ns = Namespace('earnings')
        for e in ['eps','revenue','date']:
            ns.add_const(e, f'earnings.{e}', TYPE_STRING)
        self.namespaces['earnings'] = ns
        # settlement_as_close
        ns = Namespace('settlement_as_close')
        ns.add_const('regular', 'settlement_as_close.regular', TYPE_STRING)
        ns.add_const('true', 'settlement_as_close.true', TYPE_STRING)
        self.namespaces['settlement_as_close'] = ns
        # splits
        ns = Namespace('splits')
        ns.add_const('ratio', 'splits.ratio', TYPE_STRING)
        ns.add_const('date', 'splits.date', TYPE_STRING)
        self.namespaces['splits'] = ns
        # runtime
        ns = Namespace('runtime')
        for r, t in [('version', TYPE_STRING), ('version_major', TYPE_INT), ('version_minor', TYPE_INT),
                     ('version_patch', TYPE_INT), ('is_bars_last', TYPE_BOOL), ('is_funneling', TYPE_BOOL),
                     ('max_bars_back', TYPE_INT), ('last_bar_index', TYPE_INT), ('bar_index_is_last', TYPE_BOOL)]:
            ns.add_const(r, f'runtime.{r}', t)
        self.namespaces['runtime'] = ns

    def _init_global_funcs(self):
        self.global_functions = {
            'indicator': BuiltinFunction('indicator', [Signature([
                Parameter("title", PineType(TypeKind.STRING, Qualifier.CONST)),
                Parameter("shorttitle", TYPE_INPUT_STRING, True, None),
                Parameter("overlay", TYPE_INPUT_BOOL, True, None),
                Parameter("format", TYPE_INPUT_STRING, True, None),
                Parameter("precision", TYPE_INPUT_INT, True, None),
                Parameter("scale", ENUM_SCALE, True, None),
                Parameter("max_bars_back", TYPE_INPUT_INT, True, None),
                Parameter("timeframe", TYPE_INPUT_STRING, True, None),
                Parameter("timeframe_gaps", ENUM_BARMERGE_GAPS, True, None),
                Parameter("explicit_plot_zorder", TYPE_INPUT_BOOL, True, None),
                Parameter("max_lines_count", TYPE_INPUT_INT, True, None),
                Parameter("max_labels_count", TYPE_INPUT_INT, True, None),
                Parameter("max_boxes_count", TYPE_INPUT_INT, True, None),
                Parameter("max_polylines_count", TYPE_INPUT_INT, True, None),
                Parameter("calc_bars_count", TYPE_INPUT_INT, True, None),
                Parameter("dynamic_requests", TYPE_INPUT_BOOL, True, None),
                Parameter("behind_chart", TYPE_INPUT_BOOL, True, None),
            ], TYPE_VOID)]),
            'strategy': BuiltinFunction('strategy', [Signature([
                Parameter("title", PineType(TypeKind.STRING, Qualifier.CONST)),
                Parameter("shorttitle", TYPE_INPUT_STRING, True, None),
                Parameter("overlay", TYPE_INPUT_BOOL, True, None),
                Parameter("format", TYPE_INPUT_STRING, True, None),
                Parameter("precision", TYPE_INPUT_INT, True, None),
                Parameter("scale", ENUM_SCALE, True, None),
                Parameter("initial_capital", TYPE_INPUT_FLOAT, True, None),
                Parameter("default_qty_type", TYPE_INPUT_STRING, True, None),
                Parameter("default_qty_value", TYPE_INPUT_FLOAT, True, None),
                Parameter("commission_type", TYPE_INPUT_STRING, True, None),
                Parameter("commission_value", TYPE_INPUT_FLOAT, True, None),
                Parameter("slippage", TYPE_INPUT_FLOAT, True, None),
                Parameter("margin_long", TYPE_INPUT_INT, True, None),
                Parameter("margin_short", TYPE_INPUT_INT, True, None),
                Parameter("risk_free_rate", TYPE_INPUT_FLOAT, True, None),
                Parameter("pyramiding", TYPE_INPUT_INT, True, None),
                Parameter("calc_on_every_tick", TYPE_INPUT_BOOL, True, None),
                Parameter("max_bars_back", TYPE_INPUT_INT, True, None),
                Parameter("close_entries_rule", TYPE_INPUT_STRING, True, None),
                Parameter("use_bar_magnifier", TYPE_INPUT_BOOL, True, None),
                Parameter("fill_orders_on_standard_ohlc", TYPE_INPUT_BOOL, True, None),
                Parameter("dynamic_requests", TYPE_INPUT_BOOL, True, None),
                Parameter("behind_chart", TYPE_INPUT_BOOL, True, None),
            ], TYPE_VOID)]),
            'library': BuiltinFunction('library', [Signature([
                Parameter("title", PineType(TypeKind.STRING, Qualifier.CONST)),
                Parameter("version", TYPE_STRING),
                Parameter("overlay", TYPE_BOOL, True, None),
                Parameter("precision", TYPE_INT, True, None),
            ], TYPE_VOID)]),
            'plot': BuiltinFunction('plot', [Signature([
                Parameter("series", TYPE_DYNAMIC_EXPR),
                Parameter("title", TYPE_INPUT_STRING, True, None),
                Parameter("color", TYPE_COLOR, True, None),
                Parameter("linewidth", TYPE_INPUT_INT, True, None),
                Parameter("style", ENUM_PLOT_STYLE, True, None),
                Parameter("trackprice", TYPE_INPUT_BOOL, True, None),
                Parameter("histbase", TYPE_INPUT_FLOAT, True, None),
                Parameter("offset", TYPE_INPUT_INT, True, None),
                Parameter("join", TYPE_INPUT_BOOL, True, None),
                Parameter("editable", TYPE_INPUT_BOOL, True, None),
                Parameter("show_last", TYPE_INPUT_INT, True, None),
                Parameter("display", ENUM_DISPLAY, True, None),
                Parameter("format", TYPE_INPUT_STRING, True, None),
                Parameter("precision", TYPE_INPUT_INT, True, None),
                Parameter("force_overlay", TYPE_INPUT_BOOL, True, None),
                Parameter("linestyle", ENUM_PLOT_LINESTYLE, True, None),
            ], TYPE_VOID)]),
            'hline': BuiltinFunction('hline', [Signature([
                Parameter("price", TYPE_FLOAT),
                Parameter("title", TYPE_INPUT_STRING, True, None),
                Parameter("color", TYPE_COLOR, True, None),
                Parameter("linestyle", ENUM_PLOT_LINESTYLE, True, None),
                Parameter("linewidth", TYPE_INPUT_INT, True, None),
            ], TYPE_HLINE)]),
            'plotshape': BuiltinFunction('plotshape', [Signature([
                Parameter("series", TYPE_SERIES_BOOL),
                Parameter("title", TYPE_INPUT_STRING, True, None),
                Parameter("style", ENUM_SHAPE, True, None),
                Parameter("location", ENUM_LOCATION, True, None),
                Parameter("color", TYPE_COLOR, True, None),
                Parameter("text", TYPE_INPUT_STRING, True, None),
                Parameter("textcolor", TYPE_COLOR, True, None),
                Parameter("size", ENUM_SIZE, True, None),
                Parameter("offset", TYPE_INPUT_INT, True, None),
                Parameter("display", ENUM_DISPLAY, True, None),
            ], TYPE_VOID)]),
            'plotchar': BuiltinFunction('plotchar', [Signature([
                Parameter("series", TYPE_SERIES_BOOL),
                Parameter("char", TYPE_INPUT_STRING),
                Parameter("title", TYPE_INPUT_STRING, True, None),
                Parameter("location", ENUM_LOCATION, True, None),
                Parameter("color", TYPE_COLOR, True, None),
                Parameter("size", ENUM_SIZE, True, None),
                Parameter("offset", TYPE_INPUT_INT, True, None),
            ], TYPE_VOID)]),
            'fill': BuiltinFunction('fill', [Signature([
                Parameter("plot1", TYPE_INT),
                Parameter("plot2", TYPE_INT),
                Parameter("color", TYPE_COLOR, True, None),
                Parameter("border_color", TYPE_COLOR, True, None),
                Parameter("border_style", ENUM_PLOT_LINESTYLE, True, None),
                Parameter("opacity", TYPE_INT, True, None),
                Parameter("title", TYPE_INPUT_STRING, True, None),
                Parameter("editable", TYPE_INPUT_BOOL, True, None),
                Parameter("display", ENUM_DISPLAY, True, None),
            ], TYPE_VOID)]),
            'bgcolor': BuiltinFunction('bgcolor', [Signature([
                Parameter("color", TYPE_COLOR),
                Parameter("title", TYPE_INPUT_STRING, True, None),
                Parameter("editable", TYPE_INPUT_BOOL, True, None),
            ], TYPE_VOID)]),
            'barcolor': BuiltinFunction('barcolor', [Signature([
                Parameter("color", TYPE_COLOR),
                Parameter("title", TYPE_INPUT_STRING, True, None),
            ], TYPE_VOID)]),
            'alertcondition': BuiltinFunction('alertcondition', [Signature([
                Parameter("condition", TYPE_SERIES_BOOL),
                Parameter("title", TYPE_INPUT_STRING, True, None),
                Parameter("message", TYPE_INPUT_STRING, True, None),
                Parameter("freq", ENUM_ALERT_FREQ, True, None),
            ], TYPE_VOID)]),
        }

    def _init_color(self):
        ns = Namespace('color')
        for c in ['red','green','blue','white','black','orange','purple','yellow','gray','lime','aqua','fuchsia','maroon','navy','silver','teal','olive','pink','cyan']:
            ns.add_const(c, f'color.{c}', TYPE_COLOR)
        ns.add_func('new', Signature([Parameter("color", TYPE_COLOR), Parameter("transparency", TYPE_INT, True, 0)], TYPE_COLOR))
        ns.add_func('rgb', Signature([Parameter("r", TYPE_INT), Parameter("g", TYPE_INT), Parameter("b", TYPE_INT), Parameter("a", TYPE_INT, True, 100)], TYPE_COLOR))
        ns.add_func('hsl', Signature([Parameter("hue", TYPE_FLOAT), Parameter("saturation", TYPE_FLOAT), Parameter("lightness", TYPE_FLOAT), Parameter("alpha", TYPE_FLOAT, True, 100)], TYPE_COLOR))
        ns.add_func('from_gradient', Signature([Parameter("value", TYPE_FLOAT), Parameter("bottom_value", TYPE_FLOAT), Parameter("top_value", TYPE_FLOAT), Parameter("bottom_color", TYPE_COLOR), Parameter("top_color", TYPE_COLOR)], TYPE_COLOR))
        self.namespaces['color'] = ns

    def _init_barmerge(self):
        ns = Namespace('barmerge')
        ns.add_const('gaps_off', 'barmerge.gaps.off', ENUM_BARMERGE_GAPS)
        ns.add_const('gaps_on', 'barmerge.gaps.on', ENUM_BARMERGE_GAPS)
        ns.add_const('lookahead_off', 'barmerge.lookahead.off', ENUM_BARMERGE_LOOK)
        ns.add_const('lookahead_on', 'barmerge.lookahead.on', ENUM_BARMERGE_LOOK)
        self.namespaces['barmerge'] = ns

    def _init_display_xloc_yloc_size_scale(self):
        for ns_name, enum_type in [('display', ENUM_DISPLAY), ('xloc', ENUM_XLOC), ('yloc', ENUM_YLOC), ('size', ENUM_SIZE)]:
            ns = Namespace(ns_name)
            for v in enum_type.allowed_values:
                short = v.split('.')[-1]
                ns.add_const(short, v, enum_type)
            self.namespaces[ns_name] = ns

    def _init_plot_alert_consts(self):
        ns = Namespace('plot')
        for v in ENUM_PLOT_STYLE.allowed_values:
            short = v.split('.')[-1]
            ns.add_const(f'style_{short}', v, ENUM_PLOT_STYLE)
        for v in ENUM_PLOT_LINESTYLE.allowed_values:
            short = v.split('.')[-1]
            ns.add_const(f'linestyle_{short}', v, ENUM_PLOT_LINESTYLE)
        self.namespaces['plot'] = ns
        ns = Namespace('alert')
        for v in ENUM_ALERT_FREQ.allowed_values:
            short = v.split('.')[-1]
            ns.add_const(f'freq_{short}', v, ENUM_ALERT_FREQ)
        self.namespaces['alert'] = ns

    def _init_drawing_objects(self):
        ns = Namespace('line')
        ns.add_func('new', Signature([Parameter("x1", TYPE_INT), Parameter("y1", TYPE_FLOAT), Parameter("x2", TYPE_INT), Parameter("y2", TYPE_FLOAT), Parameter("xloc", ENUM_XLOC, True, None), Parameter("extend", ENUM_EXTEND, True, None), Parameter("color", TYPE_COLOR, True, None), Parameter("style", ENUM_PLOT_LINESTYLE, True, None), Parameter("width", TYPE_INT, True, None), Parameter("force_overlay", TYPE_BOOL, True, None)], TYPE_LINE))
        ns.add_func('delete', Signature([Parameter("id", TYPE_LINE)], TYPE_VOID))
        self.namespaces['line'] = ns
        ns = Namespace('label')
        ns.add_func('new', Signature([Parameter("x", TYPE_SERIES_INT), Parameter("y", TYPE_SERIES_FLOAT), Parameter("text", TYPE_SERIES_STRING, True, None), Parameter("xloc", ENUM_XLOC, True, None), Parameter("yloc", ENUM_YLOC, True, None), Parameter("color", TYPE_COLOR, True, None), Parameter("style", ENUM_LABEL_STYLE, True, None), Parameter("textcolor", TYPE_COLOR, True, None), Parameter("size", ENUM_SIZE, True, None), Parameter("textalign", ENUM_TEXT_ALIGN, True, None), Parameter("tooltip", TYPE_STRING, True, None)], TYPE_LABEL))
        ns.add_func('delete', Signature([Parameter("id", TYPE_LABEL)], TYPE_VOID))
        self.namespaces['label'] = ns
        ns = Namespace('box')
        ns.add_func('new', Signature([Parameter("left", TYPE_INT), Parameter("top", TYPE_FLOAT), Parameter("right", TYPE_INT), Parameter("bottom", TYPE_FLOAT), Parameter("xloc", ENUM_XLOC, True, None), Parameter("yloc", ENUM_YLOC, True, None), Parameter("bgcolor", TYPE_COLOR, True, None), Parameter("border_color", TYPE_COLOR, True, None), Parameter("border_style", ENUM_PLOT_LINESTYLE, True, None), Parameter("border_width", TYPE_INT, True, None), Parameter("extend", ENUM_EXTEND, True, None), Parameter("tooltip", TYPE_STRING, True, None)], TYPE_BOX))
        ns.add_func('delete', Signature([Parameter("id", TYPE_BOX)], TYPE_VOID))
        self.namespaces['box'] = ns
        ns = Namespace('table')
        ns.add_func('new', Signature([Parameter("position", ENUM_POSITION), Parameter("columns", TYPE_INPUT_INT), Parameter("rows", TYPE_INPUT_INT), Parameter("bgcolor", TYPE_COLOR, True, None), Parameter("frame_color", TYPE_COLOR, True, None), Parameter("frame_width", TYPE_INPUT_INT, True, None), Parameter("text_color", TYPE_COLOR, True, None), Parameter("text_size", ENUM_SIZE, True, None), Parameter("text_font", TYPE_STRING, True, None), Parameter("text_style", TYPE_STRING, True, None)], TYPE_TABLE))
        ns.add_func('delete', Signature([Parameter("id", TYPE_TABLE)], TYPE_VOID))
        self.namespaces['table'] = ns
        ns = Namespace('polyline')
        ns.add_func('new', Signature([Parameter("points", ArrayType(element_type=TYPE_INT)), Parameter("curved", TYPE_BOOL, True, None), Parameter("closed", TYPE_BOOL, True, None), Parameter("xloc", ENUM_XLOC, True, None), Parameter("line_color", TYPE_COLOR, True, None), Parameter("fill_color", TYPE_COLOR, True, None), Parameter("line_style", ENUM_PLOT_LINESTYLE, True, None), Parameter("line_width", TYPE_INT, True, None), Parameter("force_overlay", TYPE_BOOL, True, None)], TYPE_POLYLINE))
        ns.add_func('delete', Signature([Parameter("id", TYPE_POLYLINE)], TYPE_VOID))
        self.namespaces['polyline'] = ns

    def _init_font_session_location(self):
        ns = Namespace('font')
        for v in ENUM_TEXT_ALIGN.allowed_values:
            short = v.split('.')[-1]
            ns.add_const(f'style_{short}', v, ENUM_TEXT_ALIGN)
        self.namespaces['font'] = ns
        ns = Namespace('session')
        ns.add_const('regular', 'session.regular', TYPE_STRING)
        ns.add_const('extended', 'session.extended', TYPE_STRING)
        ns.add_const('premarket', 'session.premarket', TYPE_STRING)
        ns.add_func('ismarket', Signature([], TYPE_SERIES_BOOL))
        ns.add_func('isregular', Signature([], TYPE_SERIES_BOOL))
        ns.add_func('isextended', Signature([], TYPE_SERIES_BOOL))
        ns.add_func('ispremarket', Signature([], TYPE_SERIES_BOOL))
        ns.add_func('ispostmarket', Signature([], TYPE_SERIES_BOOL))
        self.namespaces['session'] = ns
        ns = Namespace('location')
        for v in ENUM_LOCATION.allowed_values:
            short = v.split('.')[-1]
            ns.add_const(short, v, ENUM_LOCATION)
        self.namespaces['location'] = ns

    def _init_timeframe(self):
        ns = Namespace('timeframe')
        ns.add_const('period', 'timeframe.period', TYPE_STRING)
        ns.add_const('multiplier', 'timeframe.multiplier', TYPE_INT)
        for b in ['isseconds','isminutes','isintraday','isdaily','isweekly','ismonthly','isquarterly','isyearly','isdwm','ismulti']:
            ns.add_const(b, f'timeframe.{b}', TYPE_BOOL)
        ns.add_func('in_seconds', Signature([], TYPE_INT))
        ns.add_func('in_minutes', Signature([], TYPE_INT))
        ns.add_func('change', Signature([], TYPE_BOOL))
        self.namespaces['timeframe'] = ns

    def _init_syminfo(self):
        ns = Namespace('syminfo')
        str_fields = ['ticker','tickerid','root','prefix','description','type','currency','basecurrency','timezone','session','right','country','exchange','industry','sector']
        for s in str_fields:
            ns.add_const(s, f'syminfo.{s}', TYPE_STRING)
        float_fields = ['mintick','pointvalue','pricescale','minmov','market_cap','shares_outstanding','pe','eps','high_52w','low_52w','beta','dividend_yield','avg_volume','volatility','strike']
        for f in float_fields:
            ns.add_const(f, f'syminfo.{f}', TYPE_FLOAT)
        int_fields = ['expiration','legs_count','option_type']
        for i in int_fields:
            ns.add_const(i, f'syminfo.{i}', TYPE_INT)
        self.namespaces['syminfo'] = ns

    def _init_barstate(self):
        ns = Namespace('barstate')
        for s in ['isfirst','islast','isnew','isconfirmed','ishistory','isrealtime','islastconfirmedhistory','isgap','wasgap','isfirstsession','islastsession']:
            ns.add_const(s, f'barstate.{s}', TYPE_SERIES_BOOL)
        self.namespaces['barstate'] = ns

    def _init_ta(self):
        ns = Namespace('ta')
        ns.add_func('crossover', Signature([Parameter("a", TYPE_SERIES_FLOAT), Parameter("b", TYPE_SERIES_FLOAT)], TYPE_SERIES_BOOL))
        ns.add_func('crossunder', Signature([Parameter("a", TYPE_SERIES_FLOAT), Parameter("b", TYPE_SERIES_FLOAT)], TYPE_SERIES_BOOL))
        ns.add_func('cross', Signature([Parameter("a", TYPE_SERIES_FLOAT), Parameter("b", TYPE_SERIES_FLOAT)], TYPE_SERIES_BOOL))
        ns.add_func('rising', Signature([Parameter("source", TYPE_SERIES_FLOAT), Parameter("length", TYPE_INT, True, 14)], TYPE_SERIES_BOOL))
        ns.add_func('falling', Signature([Parameter("source", TYPE_SERIES_FLOAT), Parameter("length", TYPE_INT, True, 14)], TYPE_SERIES_BOOL))
        ns.add_func('highestbars', Signature([Parameter("source", TYPE_SERIES_FLOAT), Parameter("length", TYPE_INT)], TYPE_SERIES_INT))
        ns.add_func('lowestbars', Signature([Parameter("source", TYPE_SERIES_FLOAT), Parameter("length", TYPE_INT)], TYPE_SERIES_INT))
        ns.add_func('barssince', Signature([Parameter("condition", TYPE_SERIES_BOOL)], TYPE_SERIES_INT))
        t3 = TupleType([TYPE_SERIES_FLOAT, TYPE_SERIES_FLOAT, TYPE_SERIES_FLOAT])
        ns.add_func('macd', Signature([Parameter("source", TYPE_SERIES_FLOAT, True, None), Parameter("fast", TYPE_INT, True, 12), Parameter("slow", TYPE_INT, True, 26), Parameter("signal", TYPE_INT, True, 9)], t3))
        ns.add_func('bb', Signature([Parameter("source", TYPE_SERIES_FLOAT, True, None), Parameter("length", TYPE_INT, True, 20), Parameter("mult", TYPE_FLOAT, True, 2.0)], t3))
        ns.add_func('bbands', Signature([Parameter("source", TYPE_SERIES_FLOAT, True, None), Parameter("length", TYPE_INT, True, 20), Parameter("mult", TYPE_FLOAT, True, 2.0), Parameter("mamode", TYPE_STRING, True, "sma")], t3))
        ns.add_func('dmi', Signature([Parameter("diLength", TYPE_INT, True, 14), Parameter("adxLength", TYPE_INT, True, 14)], t3))
        ns.add_func('kc', Signature([Parameter("source", TYPE_SERIES_FLOAT, True, None), Parameter("length", TYPE_INT, True, 20), Parameter("mult", TYPE_FLOAT, True, 1.0), Parameter("use_truerange", TYPE_BOOL, True, True)], t3))
        ns.add_func('ichimoku', Signature([Parameter("conversionPeriods", TYPE_INT, True, 9), Parameter("basePeriods", TYPE_INT, True, 26), Parameter("laggingSpan2Periods", TYPE_INT, True, 52), Parameter("displacement", TYPE_INT, True, 26)], TupleType([TYPE_SERIES_FLOAT]*4)))
        ns.add_func('supertrend', Signature([Parameter("factor", TYPE_FLOAT, True, 3.0), Parameter("atrPeriod", TYPE_INT, True, 10)], TupleType([TYPE_SERIES_FLOAT, TYPE_SERIES_FLOAT])))
        ns.add_func('valuewhen', Signature([Parameter("condition", TYPE_SERIES_BOOL), Parameter("source", TYPE_SERIES_FLOAT), Parameter("occurrence", TYPE_INT, True, 0)], TYPE_SERIES_FLOAT))
        ns.add_func('pivothigh', Signature([Parameter("source", TYPE_SERIES_FLOAT), Parameter("leftbars", TYPE_INT), Parameter("rightbars", TYPE_INT)], TYPE_SERIES_FLOAT))
        ns.add_func('pivotlow', Signature([Parameter("source", TYPE_SERIES_FLOAT), Parameter("leftbars", TYPE_INT), Parameter("rightbars", TYPE_INT)], TYPE_SERIES_FLOAT))
        ns.add_func('atr', Signature([Parameter("length", TYPE_INT, True, 14)], TYPE_SERIES_FLOAT))
        ns.add_func('tr', Signature([], TYPE_SERIES_FLOAT))
        ns.add_func('sar', Signature([Parameter("start", TYPE_FLOAT, True, 0.02), Parameter("increment", TYPE_FLOAT, True, 0.02), Parameter("maximum", TYPE_FLOAT, True, 0.20)], TYPE_SERIES_FLOAT))
        ns.add_func('linearreg', Signature([Parameter("source", TYPE_SERIES_FLOAT, True, None), Parameter("length", TYPE_INT, True, 14), Parameter("offset", TYPE_INT, True, 0)], TYPE_SERIES_FLOAT))
        ns.add_func('forecast', Signature([Parameter("source", TYPE_SERIES_FLOAT, True, None), Parameter("length", TYPE_INT, True, 14), Parameter("offset", TYPE_INT, True, 0)], TYPE_SERIES_FLOAT))
        ns.add_func('tsf', Signature([Parameter("source", TYPE_SERIES_FLOAT, True, None), Parameter("length", TYPE_INT, True, 14)], TYPE_SERIES_FLOAT))
        ns.add_func('correlation', Signature([Parameter("x", TYPE_SERIES_FLOAT), Parameter("y", TYPE_SERIES_FLOAT), Parameter("length", TYPE_INT)], TYPE_SERIES_FLOAT))
        ns.add_func('covariance', Signature([Parameter("x", TYPE_SERIES_FLOAT), Parameter("y", TYPE_SERIES_FLOAT), Parameter("length", TYPE_INT)], TYPE_SERIES_FLOAT))
        for f in ['sma','ema','wma','vwma','hma','rma','kama','alma','smma','dema','tema','fwma','vidya','er','ma',
                  'rsi','stoch','stochrsi','cci','mfi','cmo','roc','tsi','williams_r','ultosc','aroon','adx','adxr',
                  'plus_di','minus_di','dx','trix','mom','bop','ao','apo','ppo','kst','dpo','psar','stdev','variance',
                  'highest','lowest','sum','avg','median','min','max','true_range','obv','pvt','accdist','wad','volume_oscillator','eom','change']:
            ns.add_func(f, Signature([Parameter("source", TYPE_SERIES_FLOAT, True, None), Parameter("length", TYPE_INT, True, 14)], TYPE_SERIES_FLOAT))
        self.namespaces['ta'] = ns

    def _init_math(self):
        ns = Namespace('math')
        ns.add_const('pi', 'math.pi', TYPE_FLOAT)
        ns.add_const('e', 'math.e', TYPE_FLOAT)
        for f in ['sqrt','exp','log','log10','log2','sin','cos','tan','asin','acos','atan','sinh','cosh','tanh','degrees','radians','fract','abs','sign','floor','ceil','trunc','round','round_to_mintick','remainder','is_nan','is_finite','random']:
            ns.add_func(f, Signature([Parameter("x", TYPE_FLOAT)], TYPE_FLOAT))
        ns.add_func('atan2', Signature([Parameter("y", TYPE_FLOAT), Parameter("x", TYPE_FLOAT)], TYPE_FLOAT))
        ns.add_func('pow', Signature([Parameter("base", TYPE_FLOAT), Parameter("exp", TYPE_FLOAT)], TYPE_FLOAT))
        ns.add_func('hypot', Signature([Parameter("x", TYPE_FLOAT), Parameter("y", TYPE_FLOAT)], TYPE_FLOAT))
        ns.add_func('max', Signature([Parameter("x", TYPE_FLOAT), Parameter("y", TYPE_FLOAT)], TYPE_FLOAT))
        ns.add_func('min', Signature([Parameter("x", TYPE_FLOAT), Parameter("y", TYPE_FLOAT)], TYPE_FLOAT))
        ns.add_func('clamp', Signature([Parameter("x", TYPE_FLOAT), Parameter("min", TYPE_FLOAT), Parameter("max", TYPE_FLOAT)], TYPE_FLOAT))
        ns.add_func('lerp', Signature([Parameter("y1", TYPE_FLOAT), Parameter("y2", TYPE_FLOAT), Parameter("x", TYPE_FLOAT)], TYPE_FLOAT))
        ns.add_func('invlerp', Signature([Parameter("y1", TYPE_FLOAT), Parameter("y2", TYPE_FLOAT), Parameter("y", TYPE_FLOAT)], TYPE_FLOAT))
        self.namespaces['math'] = ns

    def _init_str(self):
        ns = Namespace('str')
        ns.add_func('length', Signature([Parameter("s", TYPE_STRING)], TYPE_INT))
        ns.add_func('tostring', Signature([Parameter("x", TYPE_DYNAMIC_EXPR), Parameter("format", TYPE_STRING, True, "")], TYPE_STRING))
        ns.add_func('tonumber', Signature([Parameter("s", TYPE_STRING)], TYPE_FLOAT))
        ns.add_func('tobool', Signature([Parameter("s", TYPE_STRING)], TYPE_BOOL))
        for f in ['upper','lower','trim','trim_left','trim_right','reverse']:
            ns.add_func(f, Signature([Parameter("s", TYPE_STRING)], TYPE_STRING))
        ns.add_func('substring', Signature([Parameter("s", TYPE_STRING), Parameter("start", TYPE_INT), Parameter("end", TYPE_INT, True, None)], TYPE_STRING))
        ns.add_func('replace', Signature([Parameter("s", TYPE_STRING), Parameter("old", TYPE_STRING), Parameter("new", TYPE_STRING)], TYPE_STRING))
        ns.add_func('replace_all', Signature([Parameter("s", TYPE_STRING), Parameter("old", TYPE_STRING), Parameter("new", TYPE_STRING)], TYPE_STRING))
        ns.add_func('format', Signature([Parameter("fmt", TYPE_STRING), Parameter("v", TYPE_DYNAMIC_EXPR)], TYPE_STRING))
        ns.add_func('pad_left', Signature([Parameter("s", TYPE_STRING), Parameter("len", TYPE_INT), Parameter("ch", TYPE_STRING, True, " ")], TYPE_STRING))
        ns.add_func('pad_right', Signature([Parameter("s", TYPE_STRING), Parameter("len", TYPE_INT), Parameter("ch", TYPE_STRING, True, " ")], TYPE_STRING))
        ns.add_func('split', Signature([Parameter("s", TYPE_STRING), Parameter("sep", TYPE_STRING)], ArrayType(element_type=TYPE_STRING)))
        for f in ['contains','starts_with','ends_with']:
            ns.add_func(f, Signature([Parameter("s", TYPE_STRING), Parameter("sub", TYPE_STRING)], TYPE_BOOL))
        ns.add_func('is_empty', Signature([Parameter("s", TYPE_STRING)], TYPE_BOOL))
        ns.add_func('indexof', Signature([Parameter("s", TYPE_STRING), Parameter("sub", TYPE_STRING)], TYPE_INT))
        ns.add_func('last_indexof', Signature([Parameter("s", TYPE_STRING), Parameter("sub", TYPE_STRING)], TYPE_INT))
        ns.add_func('compare', Signature([Parameter("a", TYPE_STRING), Parameter("b", TYPE_STRING)], TYPE_INT))
        self.namespaces['str'] = ns

    def _init_input(self):
        ns = Namespace('input')
        ns.add_func('int', Signature([Parameter("defval", TYPE_INPUT_INT), Parameter("title", TYPE_INPUT_STRING, True, ""), Parameter("minval", TYPE_INT, True, None), Parameter("maxval", TYPE_INT, True, None), Parameter("step", TYPE_INT, True, 1), Parameter("tooltip", TYPE_INPUT_STRING, True, "")], TYPE_INT))
        ns.add_func('float', Signature([Parameter("defval", TYPE_INPUT_FLOAT), Parameter("title", TYPE_INPUT_STRING, True, ""), Parameter("minval", TYPE_FLOAT, True, None), Parameter("maxval", TYPE_FLOAT, True, None), Parameter("step", TYPE_FLOAT, True, 1.0), Parameter("tooltip", TYPE_INPUT_STRING, True, "")], TYPE_FLOAT))
        ns.add_func('bool', Signature([Parameter("defval", TYPE_INPUT_BOOL), Parameter("title", TYPE_INPUT_STRING, True, ""), Parameter("tooltip", TYPE_INPUT_STRING, True, "")], TYPE_BOOL))
        ns.add_func('string', Signature([Parameter("defval", TYPE_INPUT_STRING), Parameter("title", TYPE_INPUT_STRING, True, ""), Parameter("tooltip", TYPE_INPUT_STRING, True, "")], TYPE_STRING))
        ns.add_func('symbol', Signature([Parameter("defval", TYPE_STRING, True, ""), Parameter("title", TYPE_INPUT_STRING, True, ""), Parameter("tooltip", TYPE_INPUT_STRING, True, "")], TYPE_STRING))
        ns.add_func('timeframe', Signature([Parameter("defval", TYPE_STRING, True, ""), Parameter("title", TYPE_INPUT_STRING, True, ""), Parameter("tooltip", TYPE_INPUT_STRING, True, "")], TYPE_STRING))
        ns.add_func('session', Signature([Parameter("defval", TYPE_STRING, True, "session.regular"), Parameter("title", TYPE_INPUT_STRING, True, ""), Parameter("tooltip", TYPE_INPUT_STRING, True, "")], TYPE_STRING))
        ns.add_func('color', Signature([Parameter("defval", TYPE_INPUT_COLOR), Parameter("title", TYPE_INPUT_STRING, True, ""), Parameter("tooltip", TYPE_INPUT_STRING, True, "")], TYPE_COLOR))
        ns.add_func('source', Signature([Parameter("defval", TYPE_SERIES_FLOAT), Parameter("title", TYPE_INPUT_STRING, True, ""), Parameter("tooltip", TYPE_INPUT_STRING, True, "")], TYPE_SERIES_FLOAT))
        ns.add_func('price', Signature([Parameter("defval", TYPE_FLOAT, True, None), Parameter("title", TYPE_INPUT_STRING, True, ""), Parameter("tooltip", TYPE_INPUT_STRING, True, "")], TYPE_FLOAT))
        ns.add_func('time', Signature([Parameter("defval", TYPE_SERIES_INT, True, None), Parameter("title", TYPE_INPUT_STRING, True, ""), Parameter("tooltip", TYPE_INPUT_STRING, True, "")], TYPE_SERIES_INT))
        ns.add_func('enum', Signature([Parameter("defval", TYPE_STRING), Parameter("options", ArrayType(element_type=TYPE_STRING)), Parameter("title", TYPE_INPUT_STRING, True, ""), Parameter("tooltip", TYPE_INPUT_STRING, True, "")], TYPE_STRING))
        ns.add_func('text_area', Signature([Parameter("defval", TYPE_INPUT_STRING, True, ""), Parameter("title", TYPE_INPUT_STRING, True, ""), Parameter("tooltip", TYPE_INPUT_STRING, True, "")], TYPE_STRING))
        for f in ['group','divider','title']:
            ns.add_func(f, Signature([Parameter("text", TYPE_INPUT_STRING, True, "")], TYPE_VOID))
        self.namespaces['input'] = ns

    def _init_request(self):
        ns = Namespace('request')
        ns.add_func('security', Signature([
            Parameter("symbol", TYPE_SERIES_STRING), Parameter("timeframe", TYPE_SERIES_STRING),
            Parameter("expression", TYPE_DYNAMIC_EXPR),
            Parameter("gaps", ENUM_BARMERGE_GAPS, True, None),
            Parameter("lookahead", ENUM_BARMERGE_LOOK, True, None),
            Parameter("ignore_invalid_symbol", TYPE_INPUT_BOOL, True, None),
            Parameter("currency", ENUM_CURRENCY, True, None),
            Parameter("calc_bars_count", TYPE_INPUT_INT, True, None),
        ], TYPE_DYNAMIC_EXPR))
        ns.add_func('security_lower_tf', Signature([
            Parameter("symbol", TYPE_SERIES_STRING), Parameter("timeframe", TYPE_SERIES_STRING),
            Parameter("expression", TYPE_DYNAMIC_EXPR)
        ], ArrayType(TYPE_DYNAMIC_EXPR)))
        ns.add_func('financial', Signature([
            Parameter("symbol", TYPE_SERIES_STRING), Parameter("financial_id", TYPE_STRING),
            Parameter("period", TYPE_STRING), Parameter("currency", ENUM_CURRENCY, True, None),
            Parameter("gaps", ENUM_BARMERGE_GAPS, True, None),
        ], TYPE_SERIES_FLOAT))
        for f in ['dividends','splits','earnings']:
            ns.add_func(f, Signature([], TYPE_SERIES_FLOAT))
        ns.add_func('currency_rate', Signature([
            Parameter("from_currency", ENUM_CURRENCY), Parameter("to_currency", ENUM_CURRENCY)
        ], TYPE_SERIES_FLOAT))
        ns.add_func('economic', Signature([
            Parameter("country_code", TYPE_STRING), Parameter("field", TYPE_STRING)
        ], TYPE_SERIES_FLOAT))
        ns.add_func('seed', Signature([
            Parameter("repository", TYPE_STRING), Parameter("path", TYPE_STRING),
            Parameter("branch", TYPE_STRING, True, None)
        ], TYPE_DYNAMIC_EXPR))
        self.namespaces['request'] = ns

    def _init_collections(self):
        ns = Namespace('array')
        ns.add_func('new_bool', Signature([Parameter("size", TYPE_INT, True, 0), Parameter("value", TYPE_BOOL, True, False)], ArrayType(TYPE_BOOL)))
        ns.add_func('new_int', Signature([Parameter("size", TYPE_INT, True, 0), Parameter("value", TYPE_INT, True, 0)], ArrayType(TYPE_INT)))
        ns.add_func('new_float', Signature([Parameter("size", TYPE_INT, True, 0), Parameter("value", TYPE_FLOAT, True, 0.0)], ArrayType(TYPE_FLOAT)))
        ns.add_func('new_string', Signature([Parameter("size", TYPE_INT, True, 0), Parameter("value", TYPE_STRING, True, "")], ArrayType(TYPE_STRING)))
        ns.add_func('new_color', Signature([Parameter("size", TYPE_INT, True, 0), Parameter("value", TYPE_COLOR, True, "color.white")], ArrayType(TYPE_COLOR)))
        ns.add_func('size', Signature([Parameter("id", ArrayType(TYPE_DYNAMIC_EXPR))], TYPE_INT))
        ns.add_func('get', Signature([Parameter("id", ArrayType(TYPE_DYNAMIC_EXPR)), Parameter("index", TYPE_INT)], TYPE_DYNAMIC_EXPR))
        ns.add_func('set', Signature([Parameter("id", ArrayType(TYPE_DYNAMIC_EXPR)), Parameter("index", TYPE_INT), Parameter("value", TYPE_DYNAMIC_EXPR)], TYPE_VOID))
        ns.add_func('push', Signature([Parameter("id", ArrayType(TYPE_DYNAMIC_EXPR)), Parameter("value", TYPE_DYNAMIC_EXPR)], TYPE_VOID))
        ns.add_func('pop', Signature([Parameter("id", ArrayType(TYPE_DYNAMIC_EXPR))], TYPE_DYNAMIC_EXPR))
        ns.add_func('insert', Signature([Parameter("id", ArrayType(TYPE_DYNAMIC_EXPR)), Parameter("index", TYPE_INT), Parameter("value", TYPE_DYNAMIC_EXPR)], TYPE_VOID))
        ns.add_func('remove', Signature([Parameter("id", ArrayType(TYPE_DYNAMIC_EXPR)), Parameter("index", TYPE_INT)], TYPE_VOID))
        ns.add_func('clear', Signature([Parameter("id", ArrayType(TYPE_DYNAMIC_EXPR))], TYPE_VOID))
        ns.add_func('concat', Signature([Parameter("a", ArrayType(TYPE_DYNAMIC_EXPR)), Parameter("b", ArrayType(TYPE_DYNAMIC_EXPR))], ArrayType(TYPE_DYNAMIC_EXPR)))
        ns.add_func('slice', Signature([Parameter("id", ArrayType(TYPE_DYNAMIC_EXPR)), Parameter("from", TYPE_INT), Parameter("to", TYPE_INT, True, None)], ArrayType(TYPE_DYNAMIC_EXPR)))
        ns.add_func('sort', Signature([Parameter("id", ArrayType(TYPE_DYNAMIC_EXPR)), Parameter("order", TYPE_STRING, True, "order.ascending")], TYPE_VOID))
        ns.add_func('reverse', Signature([Parameter("id", ArrayType(TYPE_DYNAMIC_EXPR))], TYPE_VOID))
        ns.add_func('sum', Signature([Parameter("id", ArrayType(TYPE_FLOAT))], TYPE_FLOAT))
        ns.add_func('avg', Signature([Parameter("id", ArrayType(TYPE_FLOAT))], TYPE_FLOAT))
        ns.add_func('min', Signature([Parameter("id", ArrayType(TYPE_FLOAT))], TYPE_FLOAT))
        ns.add_func('max', Signature([Parameter("id", ArrayType(TYPE_FLOAT))], TYPE_FLOAT))
        ns.add_func('indexof', Signature([Parameter("id", ArrayType(TYPE_DYNAMIC_EXPR)), Parameter("value", TYPE_DYNAMIC_EXPR)], TYPE_INT))
        ns.add_func('includes', Signature([Parameter("id", ArrayType(TYPE_DYNAMIC_EXPR)), Parameter("value", TYPE_DYNAMIC_EXPR)], TYPE_BOOL))
        self.namespaces['array'] = ns
        ns = Namespace('map')
        ns.add_func('new', Signature([], MapType(TYPE_DYNAMIC_EXPR, TYPE_DYNAMIC_EXPR)))
        ns.add_func('size', Signature([Parameter("id", MapType())], TYPE_INT))
        ns.add_func('put', Signature([Parameter("id", MapType()), Parameter("key", TYPE_DYNAMIC_EXPR), Parameter("value", TYPE_DYNAMIC_EXPR)], TYPE_VOID))
        ns.add_func('get', Signature([Parameter("id", MapType()), Parameter("key", TYPE_DYNAMIC_EXPR)], TYPE_DYNAMIC_EXPR))
        ns.add_func('remove', Signature([Parameter("id", MapType()), Parameter("key", TYPE_DYNAMIC_EXPR)], TYPE_VOID))
        ns.add_func('clear', Signature([Parameter("id", MapType())], TYPE_VOID))
        ns.add_func('keys', Signature([Parameter("id", MapType())], ArrayType(TYPE_DYNAMIC_EXPR)))
        ns.add_func('values', Signature([Parameter("id", MapType())], ArrayType(TYPE_DYNAMIC_EXPR)))
        ns.add_func('contains', Signature([Parameter("id", MapType()), Parameter("key", TYPE_DYNAMIC_EXPR)], TYPE_BOOL))
        self.namespaces['map'] = ns
        ns = Namespace('matrix')
        ns.add_func('new', Signature([Parameter("rows", TYPE_INT), Parameter("columns", TYPE_INT), Parameter("value", TYPE_DYNAMIC_EXPR, True, 0)], MatrixType(TYPE_DYNAMIC_EXPR)))
        ns.add_func('get', Signature([Parameter("id", MatrixType()), Parameter("row", TYPE_INT), Parameter("col", TYPE_INT)], TYPE_DYNAMIC_EXPR))
        ns.add_func('set', Signature([Parameter("id", MatrixType()), Parameter("row", TYPE_INT), Parameter("col", TYPE_INT), Parameter("value", TYPE_DYNAMIC_EXPR)], TYPE_VOID))
        ns.add_func('rows', Signature([Parameter("id", MatrixType())], TYPE_INT))
        ns.add_func('columns', Signature([Parameter("id", MatrixType())], TYPE_INT))
        ns.add_func('transpose', Signature([Parameter("id", MatrixType())], MatrixType(TYPE_DYNAMIC_EXPR)))
        self.namespaces['matrix'] = ns

    def _init_strategy(self):
        ns = Namespace('strategy')
        ns.add_func('entry', Signature([Parameter("id", TYPE_STRING), Parameter("direction", TYPE_STRING), Parameter("qty", TYPE_FLOAT, True, 1.0)], TYPE_VOID))
        ns.add_func('exit', Signature([Parameter("id", TYPE_STRING)], TYPE_VOID))
        ns.add_func('close', Signature([Parameter("id", TYPE_STRING)], TYPE_VOID))
        ns.add_func('close_all', Signature([], TYPE_VOID))
        ns.add_func('order', Signature([Parameter("id", TYPE_STRING), Parameter("direction", TYPE_STRING), Parameter("qty", TYPE_FLOAT, True, 1.0)], TYPE_VOID))
        ns.add_func('cancel', Signature([Parameter("id", TYPE_STRING)], TYPE_VOID))
        ns.add_func('cancel_all', Signature([], TYPE_VOID))
        risk = ns.add_subns('risk')
        for f in ['allow_entry_in','cash_per_order','cash_equity','max_drawdown','max_loss','max_qty','max_orders','initial_capital','leverage']:
            risk.add_func(f, Signature([], TYPE_VOID))
        ct = ns.add_subns('closedtrades')
        for f in ['count','profit','entry_price','exit_price','max_runup','max_drawdown']:
            ct.add_func(f, Signature([], TYPE_DYNAMIC_EXPR))
        ot = ns.add_subns('opentrades')
        for f in ['count','profit','entry_price']:
            ot.add_func(f, Signature([], TYPE_DYNAMIC_EXPR))
        for f, t in [('position_size', TYPE_SERIES_FLOAT), ('position_avg_price', TYPE_SERIES_FLOAT),
                     ('equity', TYPE_SERIES_FLOAT), ('initial_capital', TYPE_FLOAT),
                     ('net_profit', TYPE_FLOAT), ('gross_profit', TYPE_FLOAT), ('gross_loss', TYPE_FLOAT),
                     ('profit_max_drawdown', TYPE_FLOAT), ('win_rate', TYPE_FLOAT), ('profit_factor', TYPE_FLOAT),
                     ('wintrades', TYPE_SERIES_INT), ('losstrades', TYPE_SERIES_INT),
                     ('total_trades', TYPE_INT), ('commission_paid', TYPE_FLOAT),
                     ('net_profit_percent', TYPE_FLOAT), ('drawdown', TYPE_FLOAT),
                     ('max_drawdown_percent', TYPE_FLOAT), ('sharpe_ratio', TYPE_FLOAT)]:
            ns.add_const(f, f'strategy.{f}', t)
        self.namespaces['strategy'] = ns

    def _init_chart(self):
        ns = Namespace('chart')
        ns.add_const('bgcolor', 'chart.bgcolor', TYPE_COLOR)
        ns.add_const('is_log_scale', 'chart.is_log_scale', TYPE_BOOL)
        ns.add_const('is_bar_time', 'chart.is_bar_time', TYPE_BOOL)
        ns.add_const('is_weekly', 'chart.is_weekly', TYPE_BOOL)
        ns.add_const('is_monthly', 'chart.is_monthly', TYPE_BOOL)
        ns.add_const('is_daily', 'chart.is_daily', TYPE_BOOL)
        ns.add_const('is_intraday', 'chart.is_intraday', TYPE_BOOL)
        ns.add_const('is_seconds', 'chart.is_seconds', TYPE_BOOL)
        ns.add_const('is_minutes', 'chart.is_minutes', TYPE_BOOL)
        ns.add_const('is_dwm', 'chart.is_dwm', TYPE_BOOL)
        ns.add_const('is_multi', 'chart.is_multi', TYPE_BOOL)
        ns.add_const('timeframe', 'chart.timeframe', TYPE_STRING)
        ns.add_const('resolution', 'chart.resolution', TYPE_STRING)
        ns.add_const('period', 'chart.period', TYPE_STRING)
        ns.add_const('multiplier', 'chart.multiplier', TYPE_INT)
        ns.add_const('in_seconds', 'chart.in_seconds', TYPE_INT)
        ns.add_const('in_minutes', 'chart.in_minutes', TYPE_INT)
        ns.add_const('first_bar_index', 'chart.first_bar_index', TYPE_SERIES_INT)
        ns.add_const('last_bar_index', 'chart.last_bar_index', TYPE_SERIES_INT)
        ns.add_const('first_bar_time', 'chart.first_bar_time', TYPE_SERIES_INT)
        ns.add_const('last_bar_time', 'chart.last_bar_time', TYPE_SERIES_INT)
        ns.add_const('bar_count', 'chart.bar_count', TYPE_SERIES_INT)
        ns.add_const('scale_left', 'chart.scale_left', TYPE_BOOL)
        ns.add_const('scale_right', 'chart.scale_right', TYPE_BOOL)
        ns.add_const('price_scale_min', 'chart.price_scale_min', TYPE_SERIES_FLOAT)
        ns.add_const('price_scale_max', 'chart.price_scale_max', TYPE_SERIES_FLOAT)
        ns.add_func('set_bgcolor', Signature([Parameter('color', TYPE_COLOR), Parameter('border_color', TYPE_COLOR, True, None), Parameter('border_width', TYPE_INT, True, None)], TYPE_VOID))
        self.namespaces['chart'] = ns

    def _init_linefill(self):
        ns = Namespace('linefill')
        ns.add_func('new', Signature([Parameter("line1", TYPE_LINE), Parameter("line2", TYPE_LINE), Parameter("color", TYPE_COLOR), Parameter("xoffset", TYPE_INT, True, 0), Parameter("yoffset", TYPE_INT, True, 0)], TYPE_LINEFILL))
        ns.add_func('delete', Signature([Parameter("id", TYPE_LINEFILL)], TYPE_VOID))
        ns.add_const('all', 'linefill.all', ArrayType(element_type=TYPE_LINEFILL))
        self.namespaces['linefill'] = ns

    def _init_log(self):
        ns = Namespace('log')
        for f in ['info','warning','error']:
            ns.add_func(f, Signature([Parameter("message", TYPE_STRING)], TYPE_VOID))
        self.namespaces['log'] = ns

    def _init_global_series(self):
        series = {
            'open': TYPE_SERIES_FLOAT, 'high': TYPE_SERIES_FLOAT, 'low': TYPE_SERIES_FLOAT, 'close': TYPE_SERIES_FLOAT,
            'volume': TYPE_SERIES_FLOAT, 'time': TYPE_SERIES_INT, 'time_close': TYPE_SERIES_INT,
            'hl2': TYPE_SERIES_FLOAT, 'hlc3': TYPE_SERIES_FLOAT, 'hlcc4': TYPE_SERIES_FLOAT, 'ohlc4': TYPE_SERIES_FLOAT,
            'bid': TYPE_SERIES_FLOAT, 'ask': TYPE_SERIES_FLOAT,
            'bar_index': TYPE_SERIES_INT, 'last_bar_index': TYPE_SERIES_INT,
            'year': TYPE_SERIES_INT, 'month': TYPE_SERIES_INT, 'dayofmonth': TYPE_SERIES_INT,
            'dayofweek': TYPE_SERIES_INT, 'hour': TYPE_SERIES_INT, 'minute': TYPE_SERIES_INT,
            'second': TYPE_SERIES_INT, 'millisecond': TYPE_SERIES_INT,
            'ticker': TYPE_STRING, 'tickerid': TYPE_STRING,
        }
        self.global_series = {name: ConstantValue(name, t) for name, t in series.items()}
