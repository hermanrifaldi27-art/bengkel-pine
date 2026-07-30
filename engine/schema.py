from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

class Priority(str, Enum):
    required = "required"
    high = "high"
    medium = "medium"
    low = "low"
    optional = "optional"

class TriggerType(str, Enum):
    compiler = "compiler"
    analyzer = "analyzer"

class Operation(str, Enum):
    inject_after = "inject_after"
    replace_pattern = "replace_pattern"
    remove_keyword = "remove_keyword"
    replace = "replace"
    move_to_global = "move_to_global"
    move_to_module = "move_to_module"
    wrap_with = "wrap_with"
    add_prefix = "add_prefix"
    add_parameter = "add_parameter"

SUPPORTED_OPERATIONS = {
    Operation.inject_after,
    Operation.replace_pattern,
    Operation.remove_keyword,
    Operation.replace,
    Operation.move_to_global,
    Operation.wrap_with,
    Operation.add_prefix,
}

@dataclass
class PineCompatibility:
    min: int = 5
    max: int = 6

@dataclass
class Compatibility:
    pine: PineCompatibility = field(default_factory=PineCompatibility)

@dataclass
class AstPattern:
    node_type: Optional[str] = None
    context: Optional[str] = None
    contains: Optional[str] = None
    not_contains: Optional[str] = None
    signature: Optional[str] = None
    function_name: Optional[Union[str, List[str]]] = None
    left_function: Optional[str] = None
    parent_scope: Optional[str] = None
    parent_module: Optional[Union[str, List[str]]] = None

@dataclass
class Trigger:
    type: TriggerType
    error_signals: Optional[List[str]] = None
    ast_patterns: Optional[List[AstPattern]] = None

@dataclass
class Parameter:
    name: str
    type: str = "string"
    source: Optional[str] = None
    required: bool = False
    default: Optional[Any] = None
    minimum: Optional[int] = None
    maximum: Optional[int] = None

@dataclass
class ActionSafety:
    reversible: bool = True
    backup_required: bool = True
    modifies_existing_logic: bool = False

@dataclass
class Action:
    operation: Operation
    language: str = "pine"
    anchor: Optional[str] = None
    template: Optional[str] = None
    target_module: Optional[str] = None
    safety: Optional[ActionSafety] = None

@dataclass
class PostCondition:
    function: Optional[str] = None
    variable: Optional[str] = None
    operator: Optional[str] = None
    value: Optional[Any] = None

@dataclass
class Verification:
    compiler: Optional[Dict[str, Any]] = None
    post_condition: Optional[PostCondition] = None

@dataclass
class Fallback:
    id: str
    condition: Optional[Dict[str, Any]] = None

@dataclass
class SourceMeta:
    extractor_version: Optional[str] = None
    detector_id: Optional[str] = None
    timestamp: Optional[Any] = None

@dataclass
class Preconditions:
    persistence: Optional[Dict[str, Any]] = None
    type_check: Optional[Dict[str, Any]] = None
    scope_check: Optional[Dict[str, Any]] = None

@dataclass
class Rule:
    id: str
    name: str
    priority: Priority
    triggers: List[Trigger]
    action: Action
    verification: Verification = field(default_factory=Verification)
    version: int = 1
    compatibility: Compatibility = field(default_factory=Compatibility)
    preconditions: Optional[Preconditions] = None
    parameters: List[Parameter] = field(default_factory=list)
    fallbacks: List[Fallback] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    signature: Optional[str] = None
    source: Optional[SourceMeta] = None

    def operation_supported(self) -> bool:
        return self.action.operation in SUPPORTED_OPERATIONS

    def is_actionable(self) -> bool:
        if not self.operation_supported():
            return False
        anchor = (self.action.anchor or "").strip()
        if anchor.upper() == "TODO":
            return False
        return True

@dataclass
class RulesFile:
    rules: List[Rule] = field(default_factory=list)

def validate_yaml_data(data: Any) -> RulesFile:
    # Implementasi sederhana: konversi dict ke dataclass
    if not isinstance(data, dict):
        raise ValueError("Data harus berupa dict")
    if "rules" in data and isinstance(data["rules"], list):
        rules_data = data["rules"]
    elif "rule" in data and isinstance(data["rule"], dict):
        rules_data = [data["rule"]]
    elif "id" in data and "name" in data:
        rules_data = [data]
    else:
        raise ValueError("Format YAML tidak dikenali")
    
    rules = []
    for r in rules_data:
        # Mapping field
        triggers = []
        for t in r.get("triggers", []):
            ttype = TriggerType(t.get("type", "compiler"))
            triggers.append(Trigger(
                type=ttype,
                error_signals=t.get("error_signals"),
                ast_patterns=[AstPattern(**p) for p in t.get("ast_patterns", [])] if t.get("ast_patterns") else None
            ))
        action = Action(
            operation=Operation(r["action"].get("operation", "inject_after")),
            language=r["action"].get("language", "pine"),
            anchor=r["action"].get("anchor"),
            template=r["action"].get("template"),
            target_module=r["action"].get("target_module"),
        )
        verif = Verification(
            compiler=r.get("verification", {}).get("compiler"),
            post_condition=PostCondition(**r.get("verification", {}).get("post_condition", {})) if r.get("verification", {}).get("post_condition") else None
        )
        rule = Rule(
            id=r["id"],
            name=r["name"],
            priority=Priority(r.get("priority", "medium")),
            triggers=triggers,
            action=action,
            verification=verif,
            version=r.get("version", 1),
            parameters=[Parameter(**p) for p in r.get("parameters", [])],
            fallbacks=[Fallback(**f) for f in r.get("fallbacks", [])],
            dependencies=r.get("dependencies", []),
            signature=r.get("signature"),
        )
        rules.append(rule)
    return RulesFile(rules=rules)

def validate_and_report(data: Any, filename: str = "<memory>") -> tuple[List[Rule], List[str]]:
    errors = []
    valid_rules = []
    try:
        doc = validate_yaml_data(data)
    except Exception as e:
        errors.append(f"{filename}: invalid — {e}")
        return [], errors
    for rule in doc.rules:
        try:
            if not rule.operation_supported():
                errors.append(f"{filename}: rule '{rule.id}' operation '{rule.action.operation.value}' not supported")
            if not rule.is_actionable() and rule.action.anchor == "TODO":
                errors.append(f"{filename}: rule '{rule.id}' anchor=TODO")
            valid_rules.append(rule)
        except Exception as e:
            errors.append(f"{filename}: rule {rule.id} — {e}")
    return valid_rules, errors
