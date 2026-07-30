# 🏗️ Bengkel Pine v2.0

**Static Analyzer & Auto-Repair Engine untuk Pine Script™ v6**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Pine Script](https://img.shields.io/badge/Pine_Script-v6-green.svg)](https://www.tradingview.com/pine-script-docs/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production_Ready-brightgreen.svg)]()

---

## 📖 Deskripsi

**Bengkel Pine** adalah mesin analisis kode statis untuk Pine Script v6 (bahasa pemrograman TradingView). Sistem ini mampu:

- 🔍 **Mendeteksi 19 jenis masalah** umum (repainting, memory leak, anti-pattern)
- 🏆 **Menilai 25 best practice** dengan confidence-weighted scoring
- 🧠 **Belajar dari kode** yang diekstrak (Pattern Extractor + Knowledge Base)
- 🔧 **Memperbaiki kode otomatis** dengan diff viewer, backup, dan rollback
- 📊 **Dashboard lengkap** dengan skor, grade, metrik, dan health check

---

## ✨ Fitur Utama

### 🔍 Detektor Masalah (19 detektor)

| Kategori | Detektor | Kode |
|----------|----------|------|
| **Data Fetching** | request.security tanpa lookahead/gaps, security dalam loop, lookahead bias | PINE0005, PINE0009, PINE0014, PINE0017 |
| **Plots** | plot/hline dalam if global, redundant plot literal | PINE0003, PINE0010, PINE0013 |
| **Objects** | label/box/line/linefill dalam if/loop | PINE0008, PINE0015 |
| **Memory** | Array/matrix unbounded, rebuild di islast | PINE0006, PINE0007, PINE0018 |
| **State** | var int = na, unused variable, magic number | PINE0001, PINE0019, PINE0016 |
| **Alert** | alertcondition dalam if global | PINE0004 |
| **Inputs** | input type mismatch | PINE0011 |
| **Strategy** | strategy dalam indicator | PINE0012 |

### 🏆 Plugin Best Practice (25 rules, 8 plugin)

| Plugin | Rules | Fokus |
|--------|-------|-------|
| **reliability** | barstate_guard, na_guard, nz_guard, nan_check | Keandalan sinyal |
| **memory** | var_usage, array_eviction, matrix_eviction, drawing_limits | Manajemen memori |
| **performance** | cached_security, step_loop, security_lower_tf_cached | Performa |
| **render** | force_overlay, hidden_plot, inline_inputs | Tampilan visual |
| **code_structure** | function_count, type_usage, method_usage | Struktur kode |
| **security** | barstate_confirmed, lookahead_off, no_future_leak | Keamanan sinyal |
| **complexity** | function_modularity, nesting_complexity | Kompleksitas |
| **dependency** | library_import, namespace_usage | Dependensi |

### 🔧 Pipeline Lengkap (P1-P5)

```

KODE PINE → Extractor (19 detektor) → Unified Auditor → Pattern Extractor
↓                                              ↓
Plugin System (25 rules)                    Knowledge Base (YAML)
↓                                              ↓
Laporan Terpadu ←────────────────── Auto-Fixer v3.0 (multi-pass, rollback)

```

---

## 🏗️ Arsitektur

```

bengkel-pine/
├── engine/
│   ├── parser.py              # Parser Pine Script v6 (Pratt parser)
│   ├── types.py               # Sistem tipe (Qualifier, EnumType, DynamicType)
│   ├── pine_builtins.py       # Registry 31 namespace resmi Pine v6
│   ├── semantic.py            # Semantic analyzer (scope, type inference)
│   ├── extractor.py           # 19 detektor masalah
│   ├── scoring.py             # Scoring engine (0-100, Grade A-E)
│   ├── unified_auditor.py     # P1: Pipeline terpadu
│   ├── pattern_extractor.py   # P2: Belajar dari kode
│   ├── auto_fixer_v3.py       # P3: Perbaikan otomatis
│   ├── knowledge_base.py      # P4: Penyimpanan terstruktur
│   ├── knowledge_base_proactive.py  # P5: Learning engine
│   ├── dashboard.py           # Dashboard per file
│   ├── main_dashboard.py      # Dashboard utama
│   ├── health_check.py        # Health check 8 modul
│   ├── contract_writer.py     # Menulis aturan ke YAML
│   ├── deduplicator.py        # Anti-duplikasi
│   └── ...
├── engine/audit/
│   ├── registry.py            # Plugin registry
│   ├── context.py             # AuditContext (type-safe)
│   ├── evidence.py            # Evidence dataclass
│   └── statistics.py          # StatisticsVisitor
├── engine/rules/              # 8 plugin, 25 rules
│   ├── reliability.py
│   ├── memory.py
│   ├── performance.py
│   ├── render.py
│   ├── code_structure.py
│   ├── security.py
│   ├── complexity.py
│   └── dependency.py
├── knowledge/bases/           # Knowledge Base
│   ├── patterns/              # 5 pola yang dipelajari
│   ├── fixes/                 # 11 aturan perbaikan
│   └── rules/                 # Siap diisi
├── kode_nyata/                # 7 kode produksi untuk validasi
├── tests/                     # Unit test
├── cli.py                     # CLI (12 subcommand)
└── README.md

```

---

## 🚀 Quick Start

### Prasyarat
- Python 3.10+
- Git

### Instalasi
```bash
git clone https://github.com/hermanrifaldi27-art/bengkel-pine.git
cd bengkel-pine
pip install -r requirements.txt
```

Perintah Dasar

```bash
# Audit lengkap (scoring + best practice + health)
python3 cli.py audit file.pine

# Skor saja
python3 cli.py score file.pine

# Dashboard lengkap
python3 cli.py dashboard file.pine

# Auto-fix (dry-run)
python3 cli.py fix file.pine

# Auto-fix (terapkan)
python3 cli.py fix file.pine --apply

# Health check
python3 cli.py health

# Lint file
python3 cli.py lint file.pine
```

---

📊 Hasil Stress Test (7 Kode Nyata)

# File Author Baris Skor Grade Masalah Best Practice
1 zeiierman_ml_rsi Zeiierman 604 92 A 1 66 pts (14/25)
2 intrabar_profile — 229 90 A 2 11 pts (5/25)
3 kioseff_volume KioseffTrading 418 95 A 1 24 pts (8/25)
4 kioseff_market KioseffTrading 1062 67 C 9 61 pts (12/25)
5 bigbeluga_liquidity BigBeluga 389 85 B 4 16 pts (4/25)
6 theultimator5_htf theUltimator5 592 ✅ Parse — — —
7 zeiierman_smart_nr Zeiierman ~400 85 B 3 —

---

🏥 Health Check

```
╔══════════════════════════════════════════════════════════╗
║  🏥 HEALTH CHECK: HEALTHY ✅                              ║
╠══════════════════════════════════════════════════════════╣
║  ✅ PARSER          : OK                                 ║
║  ✅ AST_TRAVERSAL   : OK                                 ║
║  ✅ BUILTINS        : OK (45 namespace)                  ║
║  ✅ SEMANTIC        : OK                                 ║
║  ✅ EXTRACTOR       : OK (7 detektor aktif)              ║
║  ✅ AUDIT_PLUGINS   : OK (8 plugin, 25 rules)            ║
║  ✅ STORAGE         : OK (2 fixes valid)                 ║
╚══════════════════════════════════════════════════════════╝
```

---

🤝 Kontributor

· Herman Rifaldi — Creator & Lead Developer
· AI (Claude) — Co-Developer, Code Review, Architecture Design

---

📄 Lisensi

MIT License — Lihat LICENSE untuk detail.

---

🔗 Links

· GitHub Repository
· Pine Script v6 Documentation
· TradingView

---

Dibangun dengan ❤️ untuk komunitas Pine Script Indonesia
