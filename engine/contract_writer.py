import yaml
from pathlib import Path

class ContractWriter:
    BASE_PATH = Path("knowledge/bases/fixes")

    @classmethod
    def write_rule(cls, feature, dry_run: bool = False):
        module = feature.module
        yaml_path = cls.BASE_PATH / f"module_{module}.yaml"
        yaml_path.parent.mkdir(parents=True, exist_ok=True)

        # Anchor dari feature, fallback ke template generator
        anchor = feature.anchor or cls._guess_anchor(feature)
        template = feature.tactic or cls._guess_template(feature)

        # Jika tactic kosong atau hanya berisi newline, gunakan template generator
        if not template or template.strip() == '' or 'new.new(' in template:
            template = cls._guess_template(feature)

        if yaml_path.exists():
            with open(yaml_path, 'r') as f:
                try:
                    data = yaml.safe_load(f) or {}
                except:
                    data = {}
            if not isinstance(data, dict) or 'rules' not in data:
                if data and isinstance(data, dict) and 'id' in data:
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
                'anchor': anchor,
                'language': 'pine',
                'template': template
            },
            'safety': {
                'reversible': True,
                'backup_required': True,
                'modifies_existing_logic': False
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

        with open(yaml_path, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False, indent=2, sort_keys=False)
        print(f"✅ Rule ditulis ke {yaml_path}")

    @classmethod
    def _guess_anchor(cls, feature) -> str:
        """Tebak anchor dari detector_id jika feature.anchor kosong."""
        detector = feature.detector_id
        goal = feature.goal

        if 'request_security' in detector:
            return 'request.security('
        elif 'plot_in_if' in detector:
            return goal.split(' ')[0] + '(' if ' ' in goal else 'plot('
        elif 'obj_in_if' in detector:
            return goal.split(' ')[0] + '(' if ' ' in goal else 'new('
        elif 'var_int_na' in detector:
            return 'var int '
        elif 'return_in_function' in detector:
            return 'return'
        elif 'array_unbounded' in detector:
            return 'array.push('
        elif 'matrix_unbounded' in detector:
            return 'matrix.add_row('
        elif 'alertcondition_in_if' in detector:
            return 'alertcondition('
        return 'TODO'

    @classmethod
    def _guess_template(cls, feature) -> str:
        """Tebak template perbaikan dari detector_id jika feature.tactic kosong."""
        detector = feature.detector_id
        goal = feature.goal

        if 'request_security' in detector:
            return 'request.security(..., lookahead = barmerge.lookahead_off)'
        elif 'plot_in_if' in detector:
            func = goal.split(' ')[0] if ' ' in goal else 'plot'
            return f'{func}(cond ? expr : na)'
        elif 'obj_in_if' in detector:
            func = goal.split(' ')[0] if ' ' in goal else 'obj'
            base = func.split('.')[-1] if '.' in func else func
            return f'var {base}_var = {base}.new(...)\nif condition\n    {base}_var := {base}.new(...)'
        elif 'var_int_na' in detector:
            return 'var int x = 0'
        elif 'return_in_function' in detector:
            return '// Hapus return statement'
        elif 'array_unbounded' in detector:
            return 'while array.size(arr) > limit\n    array.shift(arr)'
        elif 'matrix_unbounded' in detector:
            return 'if matrix.rows(mat) > limit\n    matrix.remove_row(mat, matrix.rows(mat) - 1)'
        elif 'alertcondition_in_if' in detector:
            return 'alertcondition(cond, title, message)'
        return '// TODO: Terapkan perbaikan sesuai aturan'
