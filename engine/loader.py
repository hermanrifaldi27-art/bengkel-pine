from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from engine.schema import Rule, validate_and_report

class RuleLoader:
    def __init__(self, base_path: str = "knowledge/bases/fixes", strict: bool = False):
        self.base_path = Path(base_path)
        self.strict = strict
        self.rules: List[Dict[str, Any]] = []
        self.validated_rules: List[Rule] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
    def load_all(self) -> List[Dict[str, Any]]:
        self.rules = []
        self.validated_rules = []
        self.errors = []
        self.warnings = []
        if not self.base_path.exists():
            self.errors.append(f"❌ Direktori tidak ditemukan: {self.base_path}")
            return []
        yaml_files = sorted(self.base_path.glob("module_*.yaml"))
        if not yaml_files:
            self.errors.append("⚠️ Tidak ada file YAML")
            return []
        for yaml_file in yaml_files:
            self._load_file(yaml_file)
        return self.rules
    def _load_file(self, yaml_file: Path):
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            self.errors.append(f"❌ Error {yaml_file.name}: {e}")
            return
        if data is None:
            return
        valid_models, report_errors = validate_and_report(data, filename=yaml_file.name)
        self.errors.extend(report_errors)
        for model in valid_models:
            if self.strict and not model.is_actionable():
                self.warnings.append(f"⏩ skip non-actionable: {model.id}")
                continue
            as_dict = {
                "id": model.id,
                "name": model.name,
                "version": model.version,
                "priority": model.priority.value,
                "compatibility": {"pine": {"min": model.compatibility.pine.min, "max": model.compatibility.pine.max}},
                "triggers": [{"type": t.type.value, "error_signals": t.error_signals, "ast_patterns": [{"node_type": p.node_type, "context": p.context, "contains": p.contains, "not_contains": p.not_contains} for p in t.ast_patterns] if t.ast_patterns else []} for t in model.triggers],
                "action": {"operation": model.action.operation.value, "anchor": model.action.anchor, "template": model.action.template, "target_module": model.action.target_module},
                "verification": {"compiler": model.verification.compiler, "post_condition": {"function": model.verification.post_condition.function, "variable": model.verification.post_condition.variable, "operator": model.verification.post_condition.operator, "value": model.verification.post_condition.value} if model.verification.post_condition else None},
                "parameters": [{"name": p.name, "type": p.type, "source": p.source, "required": p.required, "default": p.default} for p in model.parameters],
                "fallbacks": [{"id": f.id} for f in model.fallbacks],
                "dependencies": model.dependencies,
                "signature": model.signature,
            }
            self.rules.append(as_dict)
            self.validated_rules.append(model)
    def get_by_id(self, rule_id: str) -> Optional[Dict]:
        for rule in self.rules:
            if rule.get("id") == rule_id:
                return rule
        return None
    def get_errors(self) -> List[str]:
        return self.errors
    def get_warnings(self) -> List[str]:
        return self.warnings
    def summary(self) -> str:
        actionable = sum(1 for r in self.validated_rules if r.is_actionable())
        return f"Loaded {len(self.rules)} rules ({actionable} actionable, {len(self.errors)} issues)"
