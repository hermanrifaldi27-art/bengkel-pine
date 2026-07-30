#!/usr/bin/env python3
"""
Knowledge Base v2.0 — Penyimpanan pola terstruktur, query, dan integrasi Auto-Fixer.
"""
import os, yaml, hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class KnowledgeRule:
    """Satu aturan di knowledge base."""
    id: str
    category: str
    name: str
    description: str
    severity: str
    fix_template: str          # template kode perbaikan
    evidence_count: int = 0
    confidence: float = 0.0
    last_updated: str = ""
    auto_generated: bool = True

class KnowledgeBase:
    """Knowledge base terpusat untuk pola yang dipelajari dan aturan perbaikan."""

    def __init__(self, base_path: str = "knowledge/bases"):
        self.base_path = base_path
        self.patterns_path = os.path.join(base_path, "patterns")
        self.fixes_path = os.path.join(base_path, "fixes")
        self.rules_path = os.path.join(base_path, "rules")
        os.makedirs(self.patterns_path, exist_ok=True)
        os.makedirs(self.fixes_path, exist_ok=True)
        os.makedirs(self.rules_path, exist_ok=True)

    def add_rule(self, rule: KnowledgeRule) -> bool:
        """Tambahkan aturan ke knowledge base. Return False jika sudah ada."""
        yaml_path = os.path.join(self.rules_path, f"rule_{rule.id}.yaml")
        if os.path.exists(yaml_path):
            # Update existing
            try:
                with open(yaml_path, 'r') as f:
                    existing = yaml.safe_load(f) or {}
                existing['evidence_count'] = existing.get('evidence_count', 0) + 1
                existing['confidence'] = min(1.0, existing['evidence_count'] / 10.0)
                existing['last_updated'] = datetime.now().isoformat()
                with open(yaml_path, 'w') as f:
                    yaml.dump(existing, f, allow_unicode=True)
                return True
            except Exception:
                return False

        data = {
            'id': rule.id,
            'category': rule.category,
            'name': rule.name,
            'description': rule.description,
            'severity': rule.severity,
            'fix_template': rule.fix_template,
            'evidence_count': rule.evidence_count,
            'confidence': rule.confidence,
            'last_updated': datetime.now().isoformat(),
            'auto_generated': rule.auto_generated,
        }
        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, allow_unicode=True)
        return True

    def get_rules(self, category: Optional[str] = None, min_confidence: float = 0.3) -> List[dict]:
        """Ambil aturan dari knowledge base."""
        rules = []
        for fname in os.listdir(self.rules_path):
            if fname.endswith('.yaml'):
                fpath = os.path.join(self.rules_path, fname)
                try:
                    with open(fpath, 'r') as f:
                        data = yaml.safe_load(f)
                    if data and data.get('confidence', 0) >= min_confidence:
                        if category is None or data.get('category') == category:
                            rules.append(data)
                except Exception:
                    pass
        return sorted(rules, key=lambda r: r.get('confidence', 0), reverse=True)

    def get_fix_for(self, detector_id: str) -> Optional[str]:
        """Dapatkan template perbaikan untuk detector_id tertentu."""
        for rule in self.get_rules():
            if rule.get('name') == detector_id or rule.get('id') == detector_id:
                return rule.get('fix_template')
        return None

    def summary(self) -> str:
        patterns = len([f for f in os.listdir(self.patterns_path) if f.endswith('.yaml')]) if os.path.exists(self.patterns_path) else 0
        fixes = len([f for f in os.listdir(self.fixes_path) if f.endswith('.yaml')]) if os.path.exists(self.fixes_path) else 0
        rules = len([f for f in os.listdir(self.rules_path) if f.endswith('.yaml')]) if os.path.exists(self.rules_path) else 0
        return f"{patterns} patterns, {fixes} fixes, {rules} rules"
