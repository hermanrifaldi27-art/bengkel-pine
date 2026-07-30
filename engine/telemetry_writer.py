import json
from pathlib import Path
from datetime import datetime

TELEMETRY_PATH = Path("storage/telemetry/rules.json")

class TelemetryWriter:
    @staticmethod
    def record(rule_id: str, success: bool):
        """Catat penggunaan rule ke telemetry (JSON)"""
        TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing
        if TELEMETRY_PATH.exists():
            with open(TELEMETRY_PATH, 'r') as f:
                data = json.load(f)
        else:
            data = {}
        
        # Update
        if rule_id not in data:
            data[rule_id] = {
                'usage_count': 0,
                'success_count': 0,
                'failure_count': 0,
                'first_used': datetime.now().isoformat(),
                'last_used': None
            }
        
        data[rule_id]['usage_count'] += 1
        if success:
            data[rule_id]['success_count'] += 1
        else:
            data[rule_id]['failure_count'] += 1
        data[rule_id]['last_used'] = datetime.now().isoformat()
        
        # Write
        with open(TELEMETRY_PATH, 'w') as f:
            json.dump(data, f, indent=2)
        
        return data[rule_id]
    
    @staticmethod
    def get_stats(rule_id: str):
        """Ambil statistik rule dari telemetry"""
        if not TELEMETRY_PATH.exists():
            return None
        with open(TELEMETRY_PATH, 'r') as f:
            data = json.load(f)
        return data.get(rule_id)
