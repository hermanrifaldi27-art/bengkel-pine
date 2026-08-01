#!/usr/bin/env python3
"""
Test suite verifikasi silang preprocessor vs dokumentasi resmi TradingView.
"""

from preprocessor import PinePreprocessor

pp = PinePreprocessor()

total_passed = 0
total_tests = 0

def run_test(name, code, expected_lines=None, checks=None):
    global total_passed, total_tests
    print("=" * 60)
    print(f"TEST: {name}")
    print("=" * 60)
    result = pp.process(code)
    lines = result.split('\n')

    print("Output:")
    for i, line in enumerate(lines):
        print(f"  {i:2d}: {line}")

    ok = True

    # Baris per baris comparison
    if expected_lines:
        print("\nPerbandingan baris per baris:")
        max_l = max(len(lines), len(expected_lines))
        for i in range(max_l):
            actual = lines[i] if i < len(lines) else "<MISSING>"
            expect = expected_lines[i] if i < len(expected_lines) else "<EXTRA>"
            if actual == expect:
                print(f"  {i:2d}: ✅")
            else:
                print(f"  {i:2d}: ❌  Expected: {expect}")
                print(f"          Actual:   {actual}")
                ok = False

    # Structural checks
    if checks:
        print("\nVerifikasi:")
        for desc, check_fn in checks.items():
            result_check = check_fn(lines)
            status = "✅" if result_check else "❌"
            print(f"  {status} {desc}")
            if not result_check:
                ok = False

    total_tests += 1
    if ok:
        total_passed += 1
        print(f"\n  >>> ✅ PASS\n")
    else:
        print(f"\n  >>> ❌ FAIL\n")
    return ok


# ═══════════════════════════════════════════════════════════
# TEST 1: Contoh resmi dari dokumentasi TradingView
# ═══════════════════════════════════════════════════════════
sample = """//@version=2
study('Preprocessor example')
fun(x, y) =>
    if close > open // This line has one indent
        x + y // This line has two indents
    else 
        x - y
    // Some whitespace and a comment

a = sma(close, 10)
b = fun(a, 123)
c = security(tickerid, period, b)
plot(c, title='Out', color=c > c[1] ? lime : red, // This statement will be continued on the next line
     style=linebr, trackprice=true) // It's prefixed with 5 spaces, so it won't be considered as an indent
alertcondition(c > 100)
"""

expected_1 = [
    "|EMPTY|",
    "|B|study('Preprocessor example')|E|",
    "|B|fun(x, y) =>|E|",
    "|BEGIN||B|if close > open |E|",
    "|BEGIN||B|x + y |E||END||PE|",
    "|B|else |E|",
    "|BEGIN||B|x - y|E|",
    "|EMPTY|",
    "|EMPTY||END||PE||END||PE|",
    "|B|a = sma(close, 10)|E|",
    "|B|b = fun(a, 123)|E|",
    "|B|c = security(tickerid, period, b)|E|",
    "|B|plot(c, title='Out', color=c > c[1] ? lime : red, style=linebr, trackprice=true) |E|",
    "|B|alertcondition(c > 100)|E|",
    "|EMPTY|",
]

run_test("Contoh resmi TradingView", sample, expected_lines=expected_1)


# ═══════════════════════════════════════════════════════════
# TEST 2: Enum (v6)
# ═══════════════════════════════════════════════════════════
enum_code = """//@version=6
indicator("Enum test")
enum Signal
    buy = "Buy signal"
    sell = "Sell signal"
    neutral
Signal mySignal = Signal.neutral
plot(close)
"""

run_test("Enum (Pine Script v6)", enum_code, checks={
    "enum Signal ada": lambda l: any("enum Signal" in x for x in l),
    "buy field ada": lambda l: any("buy" in x for x in l),
    "sell field ada": lambda l: any("sell" in x for x in l),
    "neutral field ada": lambda l: any("neutral" in x for x in l),
    "BEGIN token ada": lambda l: any("|BEGIN|" in x for x in l),
    "END||PE token ada": lambda l: any("|END||PE|" in x for x in l),
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
    "BEGIN == END balanced": lambda l: sum(x.count("|BEGIN|") for x in l) == sum(x.count("|END|") for x in l),
})


# ═══════════════════════════════════════════════════════════
# TEST 3: UDT / Type
# ═══════════════════════════════════════════════════════════
udt_code = """//@version=6
indicator("UDT test")
type LblSettings
    bool isUp = false
    string lblStyle
    color lblColor
LblSettings infoObject = LblSettings.new()
plot(close)
"""

run_test("UDT / Type", udt_code, checks={
    "type LblSettings ada": lambda l: any("type LblSettings" in x for x in l),
    "bool isUp ada": lambda l: any("bool isUp" in x for x in l),
    "string lblStyle ada": lambda l: any("string lblStyle" in x for x in l),
    "BEGIN token ada": lambda l: any("|BEGIN|" in x for x in l),
    "END||PE token ada": lambda l: any("|END||PE|" in x for x in l),
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
    "BEGIN == END balanced": lambda l: sum(x.count("|BEGIN|") for x in l) == sum(x.count("|END|") for x in l),
})


# ═══════════════════════════════════════════════════════════
# TEST 4: Method keyword
# ═══════════════════════════════════════════════════════════
method_code = """//@version=6
indicator("Method test")
method queue(array<float> this, float value) =>
    this.push(value)
    this.size()
var array<float> data = array.new<float>()
data.queue(close)
plot(close)
"""

run_test("Method keyword", method_code, checks={
    "method queue ada": lambda l: any("method queue" in x for x in l),
    "this.push ada": lambda l: any("this.push" in x for x in l),
    "this.size ada": lambda l: any("this.size" in x for x in l),
    "=> tidak di-join (baris tersendiri)": lambda l: any("=>" in x and "|E|" in x for x in l),
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
    "BEGIN == END balanced": lambda l: sum(x.count("|BEGIN|") for x in l) == sum(x.count("|END|") for x in l),
})


# ═══════════════════════════════════════════════════════════
# TEST 5: If/else if/else
# ═══════════════════════════════════════════════════════════
ifelse_code = """//@version=6
indicator("If/else test")
int tradeDirection = if strategy.position_size < 0
    -1
else if strategy.position_size > 0
    1
else
    0
plot(close)
"""

run_test("If/else if/else", ifelse_code, checks={
    "if strategy ada": lambda l: any("if strategy" in x for x in l),
    "else if ada": lambda l: any("else if" in x for x in l),
    "else (final) ada": lambda l: any("|B|else|E|" in x for x in l),
    "BEGIN token ada": lambda l: any("|BEGIN|" in x for x in l),
    "END||PE token ada": lambda l: any("|END||PE|" in x for x in l),
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
    "BEGIN == END balanced": lambda l: sum(x.count("|BEGIN|") for x in l) == sum(x.count("|END|") for x in l),
})


# ═══════════════════════════════════════════════════════════
# TEST 6: Switch statement
# ═══════════════════════════════════════════════════════════
switch_code = """//@version=6
indicator("Switch test")
color directionColor = switch
    tradeDirection == 1  => color.new(color.blue, 90)
    tradeDirection == -1 => color.new(color.orange, 90)
    tradeDirection == 0  => na
bgcolor(directionColor)
"""

run_test("Switch statement", switch_code, checks={
    "switch keyword ada": lambda l: any("switch" in x for x in l),
    "=> arrow ada": lambda l: any("=>" in x for x in l),
    "color.blue ada": lambda l: any("color.blue" in x for x in l),
    "BEGIN token ada": lambda l: any("|BEGIN|" in x for x in l),
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
    "BEGIN == END balanced": lambda l: sum(x.count("|BEGIN|") for x in l) == sum(x.count("|END|") for x in l),
})


# ═══════════════════════════════════════════════════════════
# TEST 7: For loop + dynamic request
# ═══════════════════════════════════════════════════════════
for_code = """//@version=6
indicator("For loop test")
var array<string> symbols = array.from("NASDAQ:MSFT", "NASDAQ:AAPL")
var array<float> symCloses = array.new<float>()
for [i, sym] in symbols
    float reqClose = request.security(sym, "1D", close)
    symCloses.push(reqClose)
float avgClose = symCloses.avg()
plot(avgClose)
"""

run_test("For loop + dynamic request", for_code, checks={
    "for [i, sym] in symbols ada": lambda l: any("for [i, sym] in symbols" in x for x in l),
    "request.security ada": lambda l: any("request.security" in x for x in l),
    "symCloses.push ada": lambda l: any("symCloses.push" in x for x in l),
    "BEGIN token ada": lambda l: any("|BEGIN|" in x for x in l),
    "END||PE token ada": lambda l: any("|END||PE|" in x for x in l),
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
    "BEGIN == END balanced": lambda l: sum(x.count("|BEGIN|") for x in l) == sum(x.count("|END|") for x in l),
})


# ═══════════════════════════════════════════════════════════
# TEST 8: While loop
# ═══════════════════════════════════════════════════════════
while_code = """//@version=6
indicator("While test")
int j = 0
while j < 10
    j += 1
plot(close)
"""

run_test("While loop", while_code, checks={
    "while j < 10 ada": lambda l: any("while j < 10" in x for x in l),
    "j += 1 ada": lambda l: any("j += 1" in x for x in l),
    "BEGIN token ada": lambda l: any("|BEGIN|" in x for x in l),
    "END||PE token ada": lambda l: any("|END||PE|" in x for x in l),
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
    "BEGIN == END balanced": lambda l: sum(x.count("|BEGIN|") for x in l) == sum(x.count("|END|") for x in l),
})


# ═══════════════════════════════════════════════════════════
# TEST 9: Strategy
# ═══════════════════════════════════════════════════════════
strat_code = """//@version=6
strategy("Conditional strategy", overlay=true)
longCondition = ta.crossover(ta.sma(close, 14), ta.sma(close, 28))
if longCondition
    strategy.entry("My Long Entry Id", strategy.long)
shortCondition = ta.crossunder(ta.sma(close, 14), ta.sma(close, 28))
if shortCondition
    strategy.entry("My Short Entry Id", strategy.short)
"""

run_test("Strategy (v6)", strat_code, checks={
    "strategy declaration ada": lambda l: any("strategy(" in x for x in l),
    "if longCondition ada": lambda l: any("if longCondition" in x for x in l),
    "strategy.entry ada": lambda l: any("strategy.entry" in x for x in l),
    "BEGIN token ada": lambda l: any("|BEGIN|" in x for x in l),
    "END||PE token ada": lambda l: any("|END||PE|" in x for x in l),
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
    "BEGIN == END balanced": lambda l: sum(x.count("|BEGIN|") for x in l) == sum(x.count("|END|") for x in l),
})


# ═══════════════════════════════════════════════════════════
# TEST 10: Log statements
# ═══════════════════════════════════════════════════════════
log_code = """//@version=6
indicator("Logging test")
float ratio = (close - open) / (high - low)
if barstate.isconfirmed
    switch (high - low)
        0.0 => log.error("Division by zero")
        => log.info("Bar ratio: {0}", ratio)
plot(ratio)
"""

run_test("Log statements (v6)", log_code, checks={
    "log.error ada": lambda l: any("log.error" in x for x in l),
    "log.info ada": lambda l: any("log.info" in x for x in l),
    "switch ada": lambda l: any("switch" in x for x in l),
    "BEGIN token ada": lambda l: any("|BEGIN|" in x for x in l),
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
    "BEGIN == END balanced": lambda l: sum(x.count("|BEGIN|") for x in l) == sum(x.count("|END|") for x in l),
})


# ═══════════════════════════════════════════════════════════
# TEST 11: Deeply nested blocks
# ═══════════════════════════════════════════════════════════
# Analisis blok:
#   if close > open        → indent 0→1 = BEGIN (1)
#     for i = 0 to 5       → indent 1→2 = BEGIN (2)
#       if close[i] > ...  → indent 2→3 = BEGIN (3)
#         count += 1       → indent 3→4 = BEGIN (4) ← blok dalam if
#       else               → indent 3, tutup BEGIN(4), END
#         count -= 1       → indent 3→4 = BEGIN (4) ← blok dalam else
# Total: 4 BEGIN, 4 END (bukan 3!)
nested_code = """//@version=6
indicator("Nested test")
int count = 0
if close > open
    for i = 0 to 5
        if close[i] > open[i]
            count += 1
        else
            count -= 1
plot(count)
"""

run_test("Deeply nested (if→for→if/else)", nested_code, checks={
    "BEGIN count = 4": lambda l: sum(x.count("|BEGIN|") for x in l) == 4,
    "END count = 4": lambda l: sum(x.count("|END|") for x in l) == 4,
    "PE count = 4": lambda l: sum(x.count("|PE|") for x in l) == 4,
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
    "BEGIN == END balanced": lambda l: sum(x.count("|BEGIN|") for x in l) == sum(x.count("|END|") for x in l),
})


# ═══════════════════════════════════════════════════════════
# TEST 12: Triple nested + multiple statements
# ═══════════════════════════════════════════════════════════
triple_code = """//@version=6
indicator("Triple nested")
int x = 0
int y = 0
if close > open
    for i = 0 to 3
        x += i
        if close[i] > open[i]
            y += 1
plot(x + y)
"""

run_test("Triple nested + multiple statements", triple_code, checks={
    "BEGIN count = 3 (if, for, if)": lambda l: sum(x.count("|BEGIN|") for x in l) == 3,
    "END count = 3": lambda l: sum(x.count("|END|") for x in l) == 3,
    "x += i ada": lambda l: any("x += i" in x for x in l),
    "y += 1 ada": lambda l: any("y += 1" in x for x in l),
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
    "BEGIN == END balanced": lambda l: sum(x.count("|BEGIN|") for x in l) == sum(x.count("|END|") for x in l),
})


# ═══════════════════════════════════════════════════════════
# TEST 13: Line continuation dalam parentheses
# ═══════════════════════════════════════════════════════════
paren_code = """//@version=6
indicator("Paren test")
myPlot = plot(
     close,
     color = color.blue,
     linewidth = 2)
"""

run_test("Line continuation dalam parentheses", paren_code, checks={
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
    "BEGIN == END balanced": lambda l: sum(x.count("|BEGIN|") for x in l) == sum(x.count("|END|") for x in l),
    "close ada": lambda l: any("close" in x for x in l),
    "color.blue ada": lambda l: any("color.blue" in x for x in l),
})


# ═══════════════════════════════════════════════════════════
# TEST 14: Empty script (minimal)
# ═══════════════════════════════════════════════════════════
empty_code = """//@version=6
indicator("Empty")
plot(close)
"""

run_test("Minimal script (no blocks)", empty_code, checks={
    "Tidak ada BEGIN": lambda l: not any("|BEGIN|" in x for x in l),
    "Tidak ada END": lambda l: not any("|END|" in x for x in l),
    "plot(close) ada": lambda l: any("plot(close)" in x for x in l),
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
})


# ═══════════════════════════════════════════════════════════
# TEST 15: Multiple if blocks berturut-turut
# ═══════════════════════════════════════════════════════════
multi_if = """//@version=6
indicator("Multi if")
int a = 0
int b = 0
if close > open
    a = 1
if high > close
    b = 1
plot(a + b)
"""

run_test("Multiple if blocks berturut-turut", multi_if, checks={
    "BEGIN count = 2": lambda l: sum(x.count("|BEGIN|") for x in l) == 2,
    "END count = 2": lambda l: sum(x.count("|END|") for x in l) == 2,
    "a = 1 ada": lambda l: any("a = 1" in x for x in l),
    "b = 1 ada": lambda l: any("b = 1" in x for x in l),
    "Tidak ada |INDENT| di output": lambda l: not any("|INDENT|" in x for x in l),
    "BEGIN == END balanced": lambda l: sum(x.count("|BEGIN|") for x in l) == sum(x.count("|END|") for x in l),
})


# ═══════════════════════════════════════════════════════════
# RINGKASAN
# ═══════════════════════════════════════════════════════════
print("=" * 60)
print(f"RINGKASAN: {total_passed}/{total_tests} test PASS")
print("=" * 60)
if total_passed == total_tests:
    print("🎉 SEMUA TEST LULUS!")
else:
    print(f"⚠️  {total_tests - total_passed} test gagal")
