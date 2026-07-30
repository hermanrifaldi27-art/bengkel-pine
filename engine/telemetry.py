import json
from pathlib import Path

TELEMETRY_PATH = Path("storage/telemetry/rules.json")

def load_telemetry():
    if not TELEMETRY_PATH.exists():
        return {}
    with open(TELEMETRY_PATH, 'r') as f:
        return json.load(f)

def save_telemetry(data):
    TELEMETRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TELEMETRY_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def record_usage(rule_id: str, success: bool):
    data = load_telemetry()
    if rule_id not in data:
        data[rule_id] = {"usage_count": 0, "success_count": 0, "failure_count": 0}
    
    data[rule_id]["usage_count"] += 1
    if success:
        data[rule_id]["success_count"] += 1
    else:
        data[rule_id]["failure_count"] += 1
    
    save_telemetry(data)
    return data[rule_id]
