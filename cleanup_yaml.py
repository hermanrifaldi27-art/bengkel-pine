import os
import yaml
from pathlib import Path

BASE_PATH = Path("knowledge/bases/fixes")

def clean_rule(rule):
    """Pastikan rule sesuai schema v6.0, buang field tidak perlu"""
    cleaned = {}
    
    # Field wajib
    for field in ['id', 'name', 'version', 'priority', 'compatibility', 'triggers', 'preconditions', 'parameters', 'action', 'verification']:
        if field in rule:
            cleaned[field] = rule[field]
        else:
            # Default untuk field yang hilang
            if field == 'triggers':
                cleaned[field] = [{"type": "analyzer", "ast_patterns": []}]
            elif field == 'preconditions':
                cleaned[field] = {"persistence": {"must_be_var": True}, "type_check": {"must_be": "array"}}
            elif field == 'parameters':
                cleaned[field] = [{"name": "var", "type": "string", "source": "ast_identifier"}]
            elif field == 'action':
                cleaned[field] = {"operation": "inject_after", "anchor": "TODO", "language": "pine", "template": ""}
            elif field == 'verification':
                cleaned[field] = {"compiler": {"must_pass": True}}
            elif field == 'compatibility':
                cleaned[field] = {"pine": {"min": 5, "max": 6}}
            elif field == 'priority':
                cleaned[field] = "medium"
            elif field == 'version':
                cleaned[field] = 1
            else:
                cleaned[field] = rule.get(field, "")
    
    # Tambahkan signature jika ada
    if 'signature' in rule:
        cleaned['signature'] = rule['signature']
    if 'usage_count' in rule:
        cleaned['usage_count'] = rule['usage_count']
    
    return cleaned

def cleanup_file(filepath):
    with open(filepath, 'r') as f:
        data = yaml.safe_load(f) or {}
    
    # Jika ada field 'rule' di atas, ekstrak
    if 'rule' in data and isinstance(data['rule'], dict):
        # Pindahkan isi rule ke dalam 'rules' jika belum ada
        if 'rules' not in data:
            data['rules'] = []
        # Jika rule utama punya id, tambahkan ke rules
        main_rule = data.pop('rule')
        if main_rule.get('id'):
            # Cek apakah sudah ada di rules
            existing_ids = [r.get('id') for r in data['rules'] if r.get('id')]
            if main_rule['id'] not in existing_ids:
                data['rules'].append(main_rule)
    
    # Bersihkan setiap rule
    if 'rules' in data:
        cleaned_rules = []
        seen_ids = set()
        for rule in data['rules']:
            rule_id = rule.get('id')
            if rule_id in seen_ids:
                continue  # skip duplikat
            seen_ids.add(rule_id)
            cleaned = clean_rule(rule)
            cleaned_rules.append(cleaned)
        data['rules'] = cleaned_rules
    
    # Hapus field yang tidak perlu
    for key in ['rule', 'schema_version']:
        if key in data:
            del data[key]
    
    # Tulis kembali
    with open(filepath, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, indent=2, allow_unicode=True)
    print(f"✅ {filepath.name} dibersihkan.")

def main():
    for yaml_file in BASE_PATH.glob("module_*.yaml"):
        cleanup_file(yaml_file)
    print("\n✨ Semua file YAML telah dibersihkan dan distandarisasi.")

if __name__ == "__main__":
    main()
