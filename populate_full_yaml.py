#!/usr/bin/env python3
import os
import yaml
from pathlib import Path

# Daftar rule baru (schema v6.0)
NEW_RULES = {
    "module_state.yaml": [
        {
            "rule": {
                "id": "state.persistent_array",
                "name": "Array persisten di STATE harus pakai var",
                "version": 1,
                "priority": "required",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "array_new_call", "context": "STATE", "not_contains": "var"}]}],
                "preconditions": {"persistence": {"must_be_var": False}, "type_check": {"must_be": "array"}},
                "parameters": [{"name": "var", "type": "string", "source": "ast_identifier"}],
                "action": {"operation": "add_prefix", "anchor": "{var} = array.new", "language": "pine", "template": "var {var} = array.new"},
                "verification": {"compiler": {"must_pass": True}, "post_condition": {"function": "exists", "variable": "{var}"}}
            }
        },
        {
            "rule": {
                "id": "state.matrix_eviction",
                "name": "Matrix bank harus punya eviction (remove_row)",
                "version": 1,
                "priority": "high",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "matrix_new_call", "context": "STATE", "not_contains": "remove_row"}]}],
                "preconditions": {"persistence": {"must_be_var": True}, "type_check": {"must_be": "matrix"}},
                "parameters": [{"name": "var", "type": "string", "source": "ast_identifier"}],
                "action": {"operation": "inject_after", "anchor": "matrix.add_row", "language": "pine", "template": "if {var}.rows() > memoryDepth\n    {var}.remove_row({var}.rows() - 1)"},
                "verification": {"compiler": {"must_pass": True}}
            }
        }
    ],
    "module_functions.yaml": [
        {
            "rule": {
                "id": "functions.no_var",
                "name": "Fungsi tidak boleh mengandung var",
                "version": 1,
                "priority": "required",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "var_declaration", "context": "FUNCTIONS"}]}],
                "action": {"operation": "remove_keyword", "anchor": "var", "language": "pine", "template": ""},
                "verification": {"compiler": {"must_pass": True}}
            }
        },
        {
            "rule": {
                "id": "functions.no_return",
                "name": "Fungsi tidak boleh pakai return eksplisit",
                "version": 1,
                "priority": "required",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "compiler", "error_signals": ["line \\d+: unexpected 'return'"]}],
                "action": {"operation": "remove_keyword", "anchor": "return", "language": "pine", "template": ""},
                "verification": {"compiler": {"must_pass": True}}
            }
        }
    ],
    "module_calculations.yaml": [
        {
            "rule": {
                "id": "calc.pivot_detection_confirmed",
                "name": "Pivot detection harus pakai barstate.isconfirmed",
                "version": 1,
                "priority": "medium",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "function_call", "function_name": ["ta.pivothigh", "ta.pivotlow"], "not_contains": "barstate.isconfirmed"}]}],
                "parameters": [{"name": "pivot_func", "type": "string", "source": "ast_identifier"}],
                "action": {"operation": "replace", "language": "pine", "template": "{pivot_func}(...) and barstate.isconfirmed"},
                "verification": {"compiler": {"must_pass": True}}
            }
        },
        {
            "rule": {
                "id": "calc.matrix_remove_row",
                "name": "Matrix eviction dengan remove_row",
                "version": 1,
                "priority": "high",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "matrix_new_call", "context": "CALCULATIONS", "contains": "memoryDepth"}]}],
                "parameters": [{"name": "var", "type": "string", "source": "ast_identifier"}],
                "action": {"operation": "inject_after", "anchor": "matrix.add_row", "language": "pine", "template": "if {var}.rows() > memoryDepth\n    {var}.remove_row({var}.rows() - 1)"},
                "verification": {"compiler": {"must_pass": True}}
            }
        }
    ],
    "module_plots.yaml": [
        {
            "rule": {
                "id": "plots.plot_global",
                "name": "plot harus di global scope (PLOTS module)",
                "version": 1,
                "priority": "required",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "plot_call", "parent_module": ["CALCULATIONS", "FUNCTIONS"]}]}],
                "action": {"operation": "move_to_module", "anchor": "plot", "target_module": "PLOTS", "language": "pine", "template": "plot(...)"},
                "verification": {"compiler": {"must_pass": True}}
            }
        },
        {
            "rule": {
                "id": "plots.plotshape_confirmed",
                "name": "plotshape harus pakai barstate.isconfirmed",
                "version": 1,
                "priority": "high",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "plotshape_call", "not_contains": "barstate.isconfirmed"}]}],
                "action": {"operation": "wrap_with", "anchor": "plotshape(", "language": "pine", "template": "barstate.isconfirmed and plotshape(...)"},
                "verification": {"compiler": {"must_pass": True}}
            }
        }
    ],
    "module_drawings.yaml": [
        {
            "rule": {
                "id": "drawings.neon_glow",
                "name": "Neon glow dengan 3 layer line (outer, inner, core)",
                "version": 1,
                "priority": "low",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "line_new_call", "context": "DRAWINGS", "contains": "width"}]}],
                "action": {"operation": "replace", "language": "pine", "template": "line.new(..., width=8, color=color.new(color, 70))\nline.new(..., width=5, color=color.new(color, 40))\nline.new(..., width=2, color=color)"},
                "verification": {"compiler": {"must_pass": True}}
            }
        },
        {
            "rule": {
                "id": "drawings.dynamic_label",
                "name": "Label dinamis pakai set_xy/set_text",
                "version": 1,
                "priority": "medium",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "label_new_call", "context": "DRAWINGS", "in_loop": True}]}],
                "action": {"operation": "replace", "language": "pine", "template": "if na(label)\n    label := label.new(...)\nelse\n    label.set_xy(...)\n    label.set_text(...)"},
                "verification": {"compiler": {"must_pass": True}}
            }
        }
    ],
    "module_alert.yaml": [
        {
            "rule": {
                "id": "alert.alertcondition_global",
                "name": "alertcondition harus di global scope",
                "version": 1,
                "priority": "required",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "alertcondition_call", "parent_module": ["if", "for", "while"]}]}],
                "action": {"operation": "move_to_global", "anchor": "alertcondition", "language": "pine", "template": "alertcondition(...)"},
                "verification": {"compiler": {"must_pass": True}}
            }
        }
    ],
    "module_data_fetching.yaml": [
        {
            "rule": {
                "id": "data_fetching.footprint_guard",
                "name": "request.footprint harus pakai guard (needFootprint)",
                "version": 1,
                "priority": "required",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "request_footprint_call", "not_contains": "needFootprint"}]}],
                "action": {"operation": "wrap_with", "anchor": "request.footprint", "language": "pine", "template": "if needFootprint\n    request.footprint(...)"},
                "verification": {"compiler": {"must_pass": True}}
            }
        }
    ],
    "module_inputs.yaml": [
        {
            "rule": {
                "id": "inputs.display_none_inline",
                "name": "display.none harus pakai inline agar tetap terlihat",
                "version": 1,
                "priority": "low",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "input_declaration", "contains": "display.none", "not_contains": "inline"}]}],
                "action": {"operation": "add_parameter", "anchor": "input", "language": "pine", "template": "inline = 'group'"},
                "verification": {"compiler": {"must_pass": True}}
            }
        }
    ],
    "module_validation.yaml": [
        {
            "rule": {
                "id": "validation.syarat_lengkap",
                "name": "Harus ada validasi syaratLengkap sebelum kalkulasi",
                "version": 1,
                "priority": "high",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "variable_declaration", "context": "VALIDATION", "not_contains": "syaratLengkap"}]}],
                "action": {"operation": "inject_after", "anchor": "VALIDATION", "language": "pine", "template": "syaratLengkap = sistemAktif and inputValid and dataLengkap"},
                "verification": {"compiler": {"must_pass": True}}
            }
        }
    ],
    "module_cleanup.yaml": [
        {
            "rule": {
                "id": "cleanup.box_delete",
                "name": "Box visual harus dihapus saat tidak aktif",
                "version": 1,
                "priority": "medium",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "box_new_call", "context": "DRAWINGS", "not_contains": "delete"}]}],
                "action": {"operation": "inject_after", "anchor": "if not s.act", "language": "pine", "template": "if not na(box)\n    box.delete()\n    box := na"},
                "verification": {"compiler": {"must_pass": True}}
            }
        }
    ],
    "module_l10n.yaml": [
        {
            "rule": {
                "id": "l10n.factory_pattern",
                "name": "UDT besar (>5 field) pakai factory function",
                "version": 1,
                "priority": "low",
                "compatibility": {"pine": {"min": 5, "max": 6}},
                "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "type_declaration", "field_count": ">5", "not_contains": "factory"}]}],
                "action": {"operation": "inject_after", "anchor": "type", "language": "pine", "template": "// @UDT_FACTORY: buat fungsi f_build_{type_name}() di FUNCTIONS"},
                "verification": {"compiler": {"must_pass": True}}
            }
        }
    ]
}

def merge_rules(existing_file, new_rules):
    """Merge rule baru ke file YAML yang sudah ada, hindari duplikasi"""
    filepath = Path("knowledge/bases/fixes") / existing_file
    existing_data = {}
    
    if filepath.exists():
        with open(filepath, 'r') as f:
            existing_data = yaml.safe_load(f) or {}
    
    # Jika file belum punya struktur 'rule', inisialisasi
    if 'rule' not in existing_data:
        existing_data = {'rule': {}}
    
    # Ambil daftar rule yang sudah ada (dari file)
    existing_rules = existing_data.get('rules', [])
    existing_ids = [r.get('id') for r in existing_rules if r.get('id')]
    
    # Tambahkan rule baru yang belum ada
    added = 0
    for new_rule in new_rules:
        if new_rule['rule']['id'] not in existing_ids:
            existing_rules.append(new_rule['rule'])
            added += 1
    
    # Jika tidak ada list 'rules', buat
    existing_data['rules'] = existing_rules
    
    # Tulis kembali
    with open(filepath, 'w') as f:
        yaml.dump(existing_data, f, default_flow_style=False, indent=2, allow_unicode=True)
    
    return added

def main():
    print("📦 Populasi 36 YAML dengan rule baru...")
    os.makedirs("knowledge/bases/fixes", exist_ok=True)
    
    total_added = 0
    for filename, rules in NEW_RULES.items():
        added = merge_rules(filename, rules)
        if added > 0:
            print(f"✅ {filename}: +{added} rule baru")
        else:
            print(f"⏩ {filename}: tidak ada rule baru (sudah ada)")
        total_added += added
    
    print(f"\n📊 Total rule baru ditambahkan: {total_added}")
    print("✅ Selesai!")

if __name__ == "__main__":
    main()
