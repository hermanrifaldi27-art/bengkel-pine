import yaml
from pathlib import Path

base = Path("knowledge/bases/fixes")

for yaml_file in base.glob("module_*.yaml"):
    with open(yaml_file, 'r') as f:
        try:
            data = yaml.safe_load(f) or {}
        except:
            print(f"⚠️ Error reading {yaml_file.name}, skip")
            continue
    
    # Jika sudah ada 'rules', lanjutkan
    if 'rules' in data and isinstance(data['rules'], list):
        print(f"⏩ {yaml_file.name} already has 'rules'")
        continue
    
    # Jika tidak ada 'rules', kemungkinan data adalah satu rule di root
    if data and isinstance(data, dict) and 'id' in data:
        # Bungkus dengan rules
        fixed = {'rules': [data]}
        with open(yaml_file, 'w') as f:
            yaml.dump(fixed, f, default_flow_style=False, indent=2)
        print(f"✅ Fixed {yaml_file.name} (wrapped single rule)")
    else:
        # Buat rules kosong
        fixed = {'rules': []}
        with open(yaml_file, 'w') as f:
            yaml.dump(fixed, f, default_flow_style=False, indent=2)
        print(f"✅ Fixed {yaml_file.name} (created empty rules)")

print("✅ Done.")
