#!/usr/bin/env python3
"""Konfigurasi Terpusat Bengkel Pine — Semua bobot, ambang batas, tampilan."""
from enum import Enum

class Severity(Enum):
    ERROR = "error"; WARNING = "warning"; INFO = "info"; HINT = "hint"

class Grade(Enum):
    A = ("A", 90, 100, "Sangat Baik — Siap publikasi")
    B = ("B", 75, 89, "Baik — Perbaikan kecil disarankan")
    C = ("C", 60, 74, "Cukup — Perlu perbaikan")
    D = ("D", 40, 59, "Kurang — Banyak masalah")
    E = ("E", 0, 39, "Buruk — Perlu perombakan besar")

# ── Bobot Dasar per Kategori ──
BASE_DEDUCTION = {
    'data_fetching': 10, 'plots': 8, 'objects': 5, 'state': 3,
    'functions': 5, 'cleanup': 8, 'alert': 8,
}

# ── Pengali Bobot Berdasarkan Konteks ──
CONTEXT_MULTIPLIERS = {
    'in_loop': 1.5, 'in_if': 1.2, 'in_function': 0.8,
    'is_strategy': 1.3, 'is_indicator': 1.0, 'pine_v5': 1.1, 'pine_v6': 1.0,
}

# ── Batasan ──
MAX_DEDUCTION_PER_CATEGORY = 15
MAX_HISTORY_VERSIONS = 50
MAX_FILE_SIZE = 10 * 1024 * 1024

# ── Ambang Batas ──
PASS_THRESHOLD = 75
PUBLISH_THRESHOLD = 90

# ── Versi ──
ENGINE_VERSION = "2.0"
PINE_DEFAULT_VERSION = 6

# ── Severity per Kategori ──
CATEGORY_SEVERITY = {
    'data_fetching': Severity.ERROR, 'plots': Severity.WARNING,
    'objects': Severity.INFO, 'state': Severity.HINT,
    'functions': Severity.INFO, 'cleanup': Severity.WARNING, 'alert': Severity.WARNING,
}

# ── Risiko Kategori ──
CATEGORY_RISK = {
    'data_fetching': 'Repainting, sinyal palsu, kerugian',
    'plots': 'Error kompilasi, indikator tidak muncul',
    'objects': 'Memory leak, error runtime',
    'state': 'Nilai awal tidak terdefinisi',
    'functions': 'Kode tidak efisien',
    'cleanup': 'Memory leak, crash pada history panjang',
    'alert': 'Error kompilasi, alert tidak berfungsi',
}

# ── Tampilan ──
COLORS = {
    'A': '🟢', 'B': '🟡', 'C': '🟠', 'D': '🔴', 'E': '⭕',
    'ERROR': '❌', 'WARNING': '⚠️', 'INFO': 'ℹ️', 'HINT': '💡',
    'PASS': '✅', 'FAIL': '❌',
    'HEALTHY': '🟢', 'DEGRADED': '🟡', 'UNHEALTHY': '🔴',
    'BAR_FILL': '█', 'BAR_EMPTY': '░',
}

DISCLAIMER = "Skor menilai kualitas penulisan kode, BUKAN jaminan keuntungan trading."
