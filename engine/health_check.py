#!/usr/bin/env python3
"""
System Health Check v2.4 — Fixed AST_TRAVERSAL, StatisticsVisitor publik.
"""
import os, sys, time
from typing import Dict, Any
from engine.config import ENGINE_VERSION

class HealthStatus:
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def combine(cls, *statuses: str) -> str:
        priority = {cls.ERROR: 4, cls.DEGRADED: 3, cls.WARNING: 2, cls.HEALTHY: 1, cls.UNKNOWN: 0}
        unknown = [s for s in statuses if s not in priority]
        if unknown:
            return cls.ERROR
        return max(statuses, key=lambda s: priority.get(s, 0))

class HealthCheck:
    MIN_AST_NODES = 20
    MIN_NAMESPACES = 30
    MIN_SYMBOLS = 1
    MIN_DETECTORS = 3

    @classmethod
    def check_all(cls) -> Dict[str, Any]:
        results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'system': cls._check_system(),
            'parser': cls._check_parser(),
            'ast_traversal': cls._check_ast_traversal(),
            'builtins': cls._check_builtins(),
            'semantic': cls._check_semantic(),
            'extractor': cls._check_extractor(),
            'audit_plugins': cls._check_audit_plugins(),
            'storage': cls._check_storage(),
        }
        results['overall_health'] = cls._calculate_overall(results)
        return results

    @classmethod
    def _check_system(cls) -> Dict[str, Any]:
        return {
            'status': 'OK',
            'python_version': sys.version.split()[0],
            'platform': sys.platform,
        }

    @classmethod
    def _check_parser(cls) -> Dict[str, Any]:
        try:
            from engine.parser import PineAST
            import time
            test_code = '//@version=6\nindicator("Test")\nvar int x = 0\nif close > open\n    plot(close)'
            start = time.time()
            ast = PineAST(test_code)
            elapsed = time.time() - start
            if not hasattr(ast.root, 'body') or not ast.root.body:
                return {'status': 'WARNING', 'error': 'AST body kosong'}
            return {
                'status': 'OK',
                'parse_time_ms': round(elapsed * 1000, 2),
                'body_nodes': len(ast.root.body),
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

    @classmethod
    def _check_ast_traversal(cls) -> Dict[str, Any]:
        try:
            from engine.parser import PineAST
            from engine.audit.statistics import StatisticsVisitor
            import time

            test_code = '//@version=6\nindicator("Test")\nvar int x = 0\nif close > open\n    plot(close)'
            start = time.time()
            ast = PineAST(test_code)
            visitor = StatisticsVisitor()
            visitor.visit(ast.root)
            elapsed = time.time() - start
            if visitor.total_nodes < cls.MIN_AST_NODES:
                return {'status': 'WARNING', 'error': f'AST node count rendah: {visitor.total_nodes} (min {cls.MIN_AST_NODES})'}
            return {
                'status': 'OK',
                'total_nodes': visitor.total_nodes,
                'unique_types': len(visitor.unique_types),
                'traversal_time_ms': round(elapsed * 1000, 2),
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

    @classmethod
    def _check_builtins(cls) -> Dict[str, Any]:
        try:
            from engine.pine_builtins import BuiltinRegistry
            registry = BuiltinRegistry()
            if len(registry.namespaces) < cls.MIN_NAMESPACES:
                return {'status': 'WARNING', 'error': f'Namespace count rendah: {len(registry.namespaces)} (min {cls.MIN_NAMESPACES})'}
            return {
                'status': 'OK',
                'namespaces': len(registry.namespaces),
                'global_functions': len(registry.global_functions),
                'global_series': len(registry.global_series),
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

    @classmethod
    def _check_semantic(cls) -> Dict[str, Any]:
        try:
            from engine.parser import PineAST
            from engine.semantic import SemanticAnalyzer
            test_code = '//@version=6\nindicator("Test")\nvar int x = 0\nf() => close\ng() => open\nplot(close)'
            ast = PineAST(test_code)
            semantic = SemanticAnalyzer()
            scope = semantic.analyze(ast.root)
            symbols = scope.symbols if scope else {}
            child_count = len(scope.children) if scope else 0
            if len(symbols) < cls.MIN_SYMBOLS:
                return {'status': 'WARNING', 'error': f'Symbol count rendah: {len(symbols)} (min {cls.MIN_SYMBOLS})'}
            return {
                'status': 'OK',
                'scopes': child_count + 1 if scope else 1,
                'symbols': len(symbols),
                'nested_scopes': child_count,
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

    @classmethod
    def _check_extractor(cls) -> Dict[str, Any]:
        try:
            from engine.parser import PineAST
            from engine.extractor import FeatureExtractor
            test_code = '//@version=6\nindicator("Test")\nif close > open\n    plot(close)'
            ast = PineAST(test_code)
            extractor = FeatureExtractor(ast.root, test_code)
            features = extractor.extract_all()
            detector_methods = [m for m in dir(FeatureExtractor)
                               if m.startswith('_detect_') and callable(getattr(FeatureExtractor, m, None))]
            detector_count = len(detector_methods)
            if detector_count < cls.MIN_DETECTORS:
                return {'status': 'WARNING', 'error': f'Detector count rendah: {detector_count} (min {cls.MIN_DETECTORS})'}
            return {
                'status': 'OK',
                'features_found': len(features),
                'detectors_active': detector_count,
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

    @classmethod
    def _check_audit_plugins(cls) -> Dict[str, Any]:
        try:
            from engine.audit.registry import AuditRegistry
            reg = AuditRegistry()
            reg.load_plugins('engine/rules')
            integrity_issues = []
            for rule in reg.rules.values():
                if not rule.check_fn or not callable(rule.check_fn):
                    integrity_issues.append(f"MISSING_CHECK_FN: {rule.id}")
                if not rule.category:
                    integrity_issues.append(f"EMPTY_CATEGORY: {rule.id}")
                if rule.points < 0:
                    integrity_issues.append(f"NEGATIVE_POINTS: {rule.id} ({rule.points})")
                if not rule.description:
                    integrity_issues.append(f"EMPTY_DESC: {rule.id}")
                if rule.priority < 0:
                    integrity_issues.append(f"NEGATIVE_PRIORITY: {rule.id} ({rule.priority})")
            for pid, meta in reg.plugins.items():
                if not meta.name:
                    integrity_issues.append(f"EMPTY_PLUGIN_NAME: {pid}")
            status = 'OK' if not integrity_issues and not reg.errors else 'WARNING'
            result = {
                'status': status,
                'plugins': len(reg.plugins),
                'rules': len(reg.rules),
                'load_errors': len(reg.errors),
                'integrity_issues': len(integrity_issues),
                'categories': len(reg.list_categories()),
            }
            if integrity_issues:
                result['integrity_detail'] = integrity_issues[:5]
            if reg.errors:
                result['load_error_detail'] = reg.errors[:3]
            return result
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

    @classmethod
    def _check_storage(cls) -> Dict[str, Any]:
        try:
            import yaml
            knowledge_path = 'knowledge/bases/fixes'
            rules_path = 'knowledge/bases/rules'
            fixes_count = 0
            fixes_valid = 0
            fixes_invalid = 0
            if os.path.exists(knowledge_path) and os.path.isdir(knowledge_path):
                for f in os.listdir(knowledge_path):
                    if f.endswith('.yaml'):
                        fixes_count += 1
                        fpath = os.path.join(knowledge_path, f)
                        if os.path.isfile(fpath) and os.path.getsize(fpath) > 0:
                            try:
                                with open(fpath, 'r') as yf:
                                    yaml.safe_load(yf)
                                fixes_valid += 1
                            except Exception:
                                fixes_invalid += 1
            rules_dir_ok = os.path.exists(rules_path) and os.path.isdir(rules_path)
            status = 'OK'
            if fixes_count == 0:
                status = 'WARNING'
            elif fixes_invalid > 0:
                status = 'WARNING'
            return {
                'status': status,
                'fixes_yaml': fixes_count,
                'fixes_valid': fixes_valid,
                'fixes_invalid': fixes_invalid,
                'rules_dir_exists': rules_dir_ok,
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

    @classmethod
    def _calculate_overall(cls, results: Dict) -> str:
        statuses = []
        for key in ['parser', 'ast_traversal', 'builtins', 'semantic', 'extractor', 'audit_plugins', 'storage']:
            if key in results:
                s = results[key].get('status', 'UNKNOWN')
                if s == 'OK': statuses.append(HealthStatus.HEALTHY)
                elif s == 'ERROR': statuses.append(HealthStatus.ERROR)
                elif s == 'WARNING': statuses.append(HealthStatus.WARNING)
                else: statuses.append(HealthStatus.UNKNOWN)
        if not statuses:
            return HealthStatus.UNKNOWN + " ❓"
        overall = statuses[0]
        for s in statuses[1:]:
            overall = HealthStatus.combine(overall, s)
        icon = {'HEALTHY': '✅', 'WARNING': '⚠️', 'DEGRADED': '🔶', 'ERROR': '❌', 'UNKNOWN': '❓'}
        return f"{overall} {icon.get(overall, '❓')}"

    @classmethod
    def _fmt_line(cls, text: str) -> str:
        W = 58
        return f"║  {text[:W-4]:<{W-4}} ║"

    @classmethod
    def format_report(cls, health: Dict[str, Any]) -> str:
        W = 58
        out = []
        out.append("╔" + "═" * W + "╗")
        out.append(cls._fmt_line(f"🏥 HEALTH CHECK: {health['overall_health']}"))
        out.append(cls._fmt_line(f"🕐 {health['timestamp']}"))
        out.append("╠" + "═" * W + "╣")
        for key, value in health.items():
            if key in ('timestamp', 'overall_health'):
                continue
            if isinstance(value, dict):
                status = value.get('status', '?')
                icon = '✅' if status == 'OK' else '⚠️' if status == 'WARNING' else '❌'
                out.append(cls._fmt_line(f"{icon} {key.upper():<15} : {status}"))
                for k, v in value.items():
                    if k not in ('status', 'error', 'integrity_detail', 'load_error_detail'):
                        out.append(cls._fmt_line(f"   {k}: {v}"))
                for detail_key in ('integrity_detail', 'load_error_detail'):
                    if detail_key in value:
                        for detail in value[detail_key][:3]:
                            out.append(cls._fmt_line(f"   ⚠️  {str(detail)}"))
        out.append("╚" + "═" * W + "╝")
        return '\n'.join(out)
