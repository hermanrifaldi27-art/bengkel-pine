#!/usr/bin/env python3
import os
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional

class RuleLoader:
    """Loader untuk knowledge base YAML v6.0 — mendukung format rules: [...]"""
    
    REQUIRED_FIELDS = ['id', 'name', 'priority', 'triggers', 'action', 'verification']
    
    
    def __init__(self, base_path: str = "knowledge/bases/fixes"):
        self.base_path = Path(base_path)
        self.rules: List[Dict[str, Any]] = []
        self.errors: List[str] = []
    
    def load_all(self) -> List[Dict[str, Any]]:
        """Muat semua file YAML di direktori fixes"""
        self.rules = []
        self.errors = []
        
        if not self.base_path.exists():
            self.errors.append(f"❌ Direktori tidak ditemukan: {self.base_path}")
            return []
        
        yaml_files = list(self.base_path.glob("module_*.yaml"))
        if not yaml_files:
            self.errors.append(f"⚠️ Tidak ada file YAML di {self.base_path}")
            return []
        
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)
                
                if data is None:
                    continue
                
                # Jika ada key 'rules', ambil daftarnya
                if 'rules' in data and isinstance(data['rules'], list):
                    for rule in data['rules']:
                        if self._validate_rule(rule, yaml_file.name):
                            self.rules.append(rule)
                else:
                    # Fallback: anggap data itu sendiri adalah satu rule
                    if self._validate_rule(data, yaml_file.name):
                        self.rules.append(data)
                        
            except yaml.YAMLError as e:
                self.errors.append(f"❌ YAML Error di {yaml_file.name}: {e}")
            except Exception as e:
                self.errors.append(f"❌ Error membaca {yaml_file.name}: {e}")
        
        return self.rules
    
    def _validate_rule(self, rule: Dict, filename: str) -> bool:
        """Validasi minimal rule sesuai schema v6.0"""
        missing = [f for f in self.REQUIRED_FIELDS if f not in rule]
        if missing:
            self.errors.append(f"⚠️ {filename}: Field wajib hilang: {missing}")
            return False
        
        # Validasi priority enum
        priority = rule.get('priority')
        valid_priorities = ['required', 'high', 'medium', 'low', 'optional']
        if priority not in valid_priorities:
            self.errors.append(f"⚠️ {filename}: priority '{priority}' tidak valid. Gunakan: {valid_priorities}")
            return False
        
        # Validasi triggers minimal 1
        if not rule.get('triggers'):
            self.errors.append(f"⚠️ {filename}: minimal 1 trigger")
            return False
        
        return True
    
    def get_by_id(self, rule_id: str) -> Optional[Dict]:
        for rule in self.rules:
            if rule.get('id') == rule_id:
                return rule
        return None
    
    def get_errors(self) -> List[str]:
        return self.errors

if __name__ == "__main__":
    loader = RuleLoader()
    rules = loader.load_all()
    print(f"📊 Loaded {len(rules)} rules")
    for err in loader.get_errors():
        print(err)
    if rules:
        for r in rules[:3]:
            print(f"  - {r.get('id')} ({r.get('priority')})")
    OPTIONAL_FIELDS = ["parameters"]
