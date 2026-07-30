#!/usr/bin/env python3
"""AuditRuleRegistry v2.4 — Duplikasi detection, metadata wajib, validasi penuh."""
import importlib, os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from engine.config import Severity, VALID_AUDIT_CATEGORIES

@dataclass
class AuditRule:
    id: str; name: str; category: str; description: str; points: int
    severity: Severity; priority: int = 100; check_fn: Any = None
    experimental: bool = False

@dataclass
class PluginMeta:
    name: str; version: str = "1.0"; author: str = "Bengkel-Pine"
    pine_version: int = 6; description: str = ""

class AuditRegistry:
    def __init__(self):
        self.rules: Dict[str, AuditRule] = {}
        self.names: Dict[str, str] = {}  # name -> id
        self.plugins: Dict[str, PluginMeta] = {}
        self.errors: List[str] = []
        self.duplicates: List[str] = []

    def add(self, *args, **kwargs) -> bool:
        if len(args) == 1 and isinstance(args[0], AuditRule):
            rule = args[0]
        else:
            rule = AuditRule(*args, **kwargs)

        # Deteksi duplikat ID
        if rule.id in self.rules:
            self.duplicates.append(f"DUPLICATE_ID: {rule.id} ({rule.name})")
            return False

        # Deteksi duplikat nama dalam kategori yang sama
        for existing_id, existing_rule in self.rules.items():
            if existing_rule.name == rule.name and existing_rule.category == rule.category:
                self.errors.append(f"DUPLICATE_NAME: {rule.name} in {rule.category} (existing: {existing_id})")

        # Validasi points
        if rule.points < 0 or rule.points > 100:
            self.errors.append(f"INVALID_POINTS: {rule.id} ({rule.points})")

        # Validasi priority
        if rule.priority < 0:
            self.errors.append(f"INVALID_PRIORITY: {rule.id} ({rule.priority})")

        # Validasi kategori
        if rule.category not in VALID_AUDIT_CATEGORIES:
            self.errors.append(f"UNKNOWN_CATEGORY: {rule.id} '{rule.category}'")

        self.rules[rule.id] = rule
        self.names[rule.name] = rule.id
        return True

    def load_plugins(self, plugin_dir: str = "engine/rules"):
        if not os.path.isdir(plugin_dir): return
        for fname in sorted(os.listdir(plugin_dir)):
            if fname.startswith('_') or not fname.endswith('.py'): continue
            modname = f"{plugin_dir.replace('/', '.')}.{fname[:-3]}"
            try:
                mod = importlib.import_module(modname)
                if not hasattr(mod, 'register'):
                    self.errors.append(f"INVALID_PLUGIN: {fname} tidak memiliki register()")
                    continue
                if hasattr(mod, 'PLUGIN_META'):
                    self.plugins[fname[:-3]] = PluginMeta(**mod.PLUGIN_META)
                else:
                    self.errors.append(f"MISSING_META: {fname} tidak memiliki PLUGIN_META")
                mod.register(self)
            except Exception as e:
                self.errors.append(f"LOAD_ERROR {fname}: {e}")

    def get_integrity_report(self) -> List[str]:
        issues = list(self.duplicates)
        for rule in self.rules.values():
            if not rule.check_fn or not callable(rule.check_fn):
                issues.append(f"MISSING_CHECK_FN: {rule.id}")
            if not rule.description:
                issues.append(f"EMPTY_DESC: {rule.id}")
        for pid, meta in self.plugins.items():
            if not meta.name:
                issues.append(f"EMPTY_PLUGIN_NAME: {pid}")
        return issues

    def get_sorted_rules(self) -> List[AuditRule]:
        return sorted(self.rules.values(), key=lambda r: r.priority)

    def get_by_category(self, category: str) -> List[AuditRule]:
        return [r for r in self.rules.values() if r.category == category]

    def list_categories(self) -> List[str]:
        return sorted(set(r.category for r in self.rules.values()))

    def get_active_rules(self) -> List[AuditRule]:
        return [r for r in self.rules.values() if not r.experimental]

    def summary(self) -> str:
        return f"{len(self.rules)} rules, {len(self.plugins)} plugins, {len(self.errors)} errors, {len(self.duplicates)} duplicates"
