#!/usr/bin/env python3
"""
AuditRuleRegistry v2 — Plugin loader, metadata, ID permanen, validasi duplikasi.
"""
import importlib, os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from engine.config import Severity

@dataclass
class AuditRule:
    id: str                       # ID permanen: BP-R001
    name: str                     # Nama deskriptif: barstate_guard
    category: str                 # reliability, memory, performance, dll.
    description: str
    points: int
    severity: Severity
    check_fn: Any                 # Callable[[dict], bool]
    priority: int = 100           # Semakin kecil = dieksekusi lebih dulu
    requires_ast: bool = True
    requires_cfg: bool = False
    requires_symbol_table: bool = False
    requires_tokens: bool = False
    experimental: bool = False

@dataclass
class PluginMeta:
    name: str
    version: str = "1.0"
    author: str = "Bengkel-Pine"
    pine_version: int = 6
    description: str = ""

class AuditRegistry:
    def __init__(self):
        self.rules: Dict[str, AuditRule] = {}   # id -> rule
        self.plugins: Dict[str, PluginMeta] = {}
        self.errors: List[str] = []

    def add(self, rule: AuditRule) -> bool:
        """Tambahkan rule. Return False jika duplikat."""
        if rule.id in self.rules:
            self.errors.append(f"Duplikat ID rule: {rule.id} ({rule.name})")
            return False
        self.rules[rule.id] = rule
        return True

    def load_plugins(self, plugin_dir: str = "engine/rules"):
        """Muat semua plugin dari direktori rules."""
        if not os.path.isdir(plugin_dir):
            return
        for fname in sorted(os.listdir(plugin_dir)):
            if fname.startswith('_') or not fname.endswith('.py'):
                continue
            modname = f"{plugin_dir.replace('/', '.')}.{fname[:-3]}"
            try:
                mod = importlib.import_module(modname)
                # Muat metadata plugin (opsional)
                if hasattr(mod, 'PLUGIN_META'):
                    meta = mod.PLUGIN_META
                    self.plugins[fname[:-3]] = PluginMeta(**meta)
                # Daftarkan rule
                if hasattr(mod, 'register'):
                    mod.register(self)
            except Exception as e:
                self.errors.append(f"Gagal muat plugin {fname}: {e}")

    def get_sorted_rules(self) -> List[AuditRule]:
        """Kembalikan rule yang diurutkan berdasarkan prioritas."""
        return sorted(self.rules.values(), key=lambda r: r.priority)

    def get_by_category(self, category: str) -> List[AuditRule]:
        return [r for r in self.rules.values() if r.category == category]

    def list_categories(self) -> List[str]:
        return sorted(set(r.category for r in self.rules.values()))

    def enable(self, rule_id: str):
        if rule_id in self.rules:
            self.rules[rule_id].experimental = False

    def disable(self, rule_id: str):
        if rule_id in self.rules:
            self.rules[rule_id].experimental = True

    def get_active_rules(self) -> List[AuditRule]:
        return [r for r in self.rules.values() if not r.experimental]

    def summary(self) -> str:
        return f"{len(self.rules)} rules, {len(self.plugins)} plugins, {len(self.errors)} errors"
