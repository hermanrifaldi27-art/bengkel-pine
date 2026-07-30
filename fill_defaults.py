import yaml
from pathlib import Path

base = Path("knowledge/bases/fixes")

DEFAULTS = {
    'id': 'auto.generated',
    'name': 'Auto-generated rule',
    'priority': 'medium',
    'triggers': [{'type': 'analyzer', 'ast_patterns': []}],
    'action': {'operation': 'inject_after', 'anchor': 'TODO', 'language': 'pine', 'template': ''},
    'verification': {'compiler': {'must_pass': True}}
}

for yaml_file in base.glob("module_*.yaml"):
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f) or {}
    
    if 'rules' not in data:
        continue
    
    changed = False
    for rule in data['rules']:
        for field, default in DEFAULTS.items():
            if field not in rule:
                rule[field] = default
                changed = True
    
    if changed:
        with open(yaml_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, indent=2)
        print(f"✅ Filled defaults in {yaml_file.name}")

print("✅ Done.")
