import yaml
from pathlib import Path
from engine.extractor import Feature

class ContractWriter:
    BASE_PATH = Path("knowledge/bases/fixes")
    
    @classmethod
    def write_rule(cls, feature: Feature, dry_run: bool = False):
        module = feature.module
        yaml_path = cls.BASE_PATH / f"module_{module}.yaml"
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing data
        if yaml_path.exists():
            with open(yaml_path, 'r') as f:
                try:
                    data = yaml.safe_load(f) or {}
                except:
                    data = {}
            # Migrasi: jika data tidak punya 'rules', buat struktur baru
            if not isinstance(data, dict) or 'rules' not in data:
                # Coba cari rule yang tersebar di root
                if data and isinstance(data, dict) and 'id' in data:
                    # Format lama: satu rule di root → pindahkan ke rules
                    data = {'rules': [data]}
                else:
                    data = {'rules': []}
        else:
            data = {'rules': []}
        
        # Cek duplikat
        existing_signatures = [r.get('signature') for r in data['rules'] if r.get('signature')]
        if feature.signature in existing_signatures:
            print(f"⏩ Rule sudah ada: {feature.signature}")
            return
        
        # Tambahkan rule
        rule = {
            'id': f"{module}.{feature.detector_id}.{feature.signature}",
            'name': feature.goal,
            'version': 1,
            'priority': 'medium',
            'compatibility': {'pine': {'min': 5, 'max': 6}},
            'triggers': [{
                'type': 'analyzer',
                'ast_patterns': [{
                    'node_type': 'pattern_match',
                    'context': feature.context,
                    'signature': feature.signature
                }]
            }],
            'preconditions': {},
            'parameters': [],
            'action': {
                'operation': 'inject_after',
                'anchor': 'TODO',
                'language': 'pine',
                'template': feature.tactic,
                'safety': {
                    'reversible': True,
                    'backup_required': True,
                    'modifies_existing_logic': False
                }
            },
            'verification': {'compiler': {'must_pass': True}},
            'fallbacks': [],
            'dependencies': [],
            'signature': feature.signature,
            'source': {
                'extractor_version': 'v2.1',
                'detector_id': feature.detector_id
            }
        }
        data['rules'].append(rule)
        
        # Write
        with open(yaml_path, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False, indent=2, sort_keys=False)
        print(f"✅ Rule ditulis ke {yaml_path}")
