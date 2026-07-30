import os
import yaml

# Schema v6.0 rules
rules_data = {
    "module_cleanup.yaml": {
        "rule": {
            "id": "cleanup.fifo.shift",
            "name": "Eviction array FIFO (while + shift)",
            "version": 1,
            "priority": "required",
            "compatibility": {"pine": {"min": 5, "max": 6}},
            "triggers": [
                {"type": "compiler", "error_signals": ["line \\d+: .*array.*size.*", "line \\d+: .*maximum.*array.*"]},
                {"type": "analyzer", "ast_patterns": [{"node_type": "comparison", "left_function": "array.size", "left_var": "{var}", "operator": ">", "right_type": ["integer", "identifier"]}]}
            ],
            "preconditions": {
                "persistence": {"must_be_var": True, "must_be_initialized": True},
                "type_check": {"must_be": "array"},
                "scope_check": {"allowed_scopes": ["global", "module"]}
            },
            "parameters": [
                {"name": "var", "type": "string", "source": "ast_identifier"},
                {"name": "limit", "type": "int", "default": 100, "minimum": 1, "maximum": 50000}
            ],
            "action": {
                "operation": "inject_after",
                "anchor": "array.push({var})",
                "language": "pine",
                "template": "while array.size({var}) > {limit}\n    array.shift({var})",
                "safety": {"reversible": True, "backup_required": True, "modifies_existing_logic": False}
            },
            "verification": {
                "compiler": {"must_pass": True},
                "post_condition": {"function": "array.size", "variable": "{var}", "operator": "<=", "value": "{limit}"}
            },
            "fallbacks": [
                {"id": "cleanup.array.remove_index", "condition": {"shift_supported": False}},
                {"id": "cleanup.array.slice_assign", "condition": {"fifo_required": False}}
            ],
            "dependencies": ["state.variable.resolve"]
        }
    },
    "module_state.yaml": {
        "rule": {
            "id": "state.matrix.bank",
            "name": "Gunakan matrix untuk bank data historis",
            "version": 1,
            "priority": "high",
            "compatibility": {"pine": {"min": 5, "max": 6}},
            "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "matrix_new_call", "context": "STATE"}]}],
            "preconditions": {"persistence": {"must_be_var": True, "must_be_initialized": True}, "type_check": {"must_be": "matrix"}},
            "parameters": [{"name": "var", "type": "string", "source": "ast_identifier"}, {"name": "cols", "type": "int", "default": 9}],
            "action": {"operation": "inject_after", "anchor": "var {var} = matrix.new", "language": "pine", "template": "// Bank data fitur historis\n// Eviction: if rows > memoryDepth: remove_row"},
            "verification": {"compiler": {"must_pass": True}}
        }
    },
    "module_calculations.yaml": {
        "rule": {
            "id": "calc.knn.weighted_voting",
            "name": "KNN distance-weighted voting",
            "version": 1,
            "priority": "medium",
            "compatibility": {"pine": {"min": 5, "max": 6}},
            "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "for_loop", "context": "CALCULATIONS", "contains": "kNeighbors"}]}],
            "parameters": [{"name": "neighbors_var", "type": "string", "source": "ast_identifier"}],
            "action": {"operation": "inject_after", "anchor": "for", "language": "pine", "template": "// Weighted voting: w = 1/(1+distance)"},
            "verification": {"compiler": {"must_pass": True}}
        }
    },
    "module_alert.yaml": {
        "rule": {
            "id": "alert.dynamic.guard",
            "name": "Alert() dinamis dengan barstate.isconfirmed",
            "version": 1,
            "priority": "required",
            "compatibility": {"pine": {"min": 5, "max": 6}},
            "triggers": [{"type": "compiler", "error_signals": ["line \\d+: alert\\(\\)"]}],
            "action": {"operation": "inject_after", "anchor": "alert(", "language": "pine", "template": "if barstate.isconfirmed\n    alert(...)"},
            "verification": {"compiler": {"must_pass": True}}
        }
    },
    "module_data_fetching.yaml": {
        "rule": {
            "id": "data_fetching.request_security.lookahead_off",
            "name": "request.security dengan lookahead_off",
            "version": 1,
            "priority": "medium",
            "compatibility": {"pine": {"min": 5, "max": 6}},
            "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "request_security_call", "not_contains": "lookahead_off"}]}],
            "action": {"operation": "replace", "language": "pine", "template": "request.security(syminfo.tickerid, tf, expr, lookahead = barmerge.lookahead_off)"},
            "verification": {"compiler": {"must_pass": True}}
        }
    },
    "module_drawings.yaml": {
        "rule": {
            "id": "drawings.polyline.zone_fill",
            "name": "Polyline zone dengan fill",
            "version": 1,
            "priority": "low",
            "compatibility": {"pine": {"min": 5, "max": 6}},
            "triggers": [{"type": "analyzer", "ast_patterns": [{"node_type": "polyline_new_call", "contains": "closed=true"}]}],
            "action": {"operation": "replace", "language": "pine", "template": "polyline.new(points, curved=false, closed=true, line_color=border, fill_color=bg)"},
            "verification": {"compiler": {"must_pass": True}}
        }
    }
}

# Buat direktori jika belum ada
os.makedirs("knowledge/bases/fixes", exist_ok=True)

for filename, data in rules_data.items():
    filepath = os.path.join("knowledge/bases/fixes", filename)
    with open(filepath, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, indent=2, allow_unicode=True)
    print(f"✅ {filename} berhasil dibuat.")

print("\n📊 Total 6 rule YAML siap digunakan.")
