#!/usr/bin/env python3
"""
System Health Check — Periksa kesehatan seluruh engine
"""
import os
import sys
import time
from typing import Dict, Any, List

class HealthCheck:
    """Periksa kesehatan sistem Bengkel Pine."""

    @classmethod
    def check_all(cls) -> Dict[str, Any]:
        """Jalankan semua pemeriksaan."""
        results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'system': cls._check_system(),
            'parser': cls._check_parser(),
            'builtins': cls._check_builtins(),
            'semantic': cls._check_semantic(),
            'extractor': cls._check_extractor(),
            'storage': cls._check_storage(),
        }
        results['overall_health'] = cls._calculate_overall(results)
        return results

    @classmethod
    def _check_system(cls) -> Dict[str, Any]:
        return {
            'python_version': sys.version,
            'platform': sys.platform,
            'memory_mb': cls._get_memory_usage(),
        }

    @classmethod
    def _check_parser(cls) -> Dict[str, Any]:
        try:
            from engine.parser import PineAST
            test_code = '//@version=6\nindicator("Test")\nplot(close)'
            start = time.time()
            ast = PineAST(test_code)
            elapsed = time.time() - start
            return {
                'status': 'OK',
                'parse_time_ms': round(elapsed * 1000, 2),
                'ast_nodes': len(ast.root.body),
                'symbols': len(ast.get_symbols()),
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

    @classmethod
    def _check_builtins(cls) -> Dict[str, Any]:
        try:
            from engine.pine_builtins import BuiltinRegistry
            registry = BuiltinRegistry()
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
            test_code = '//@version=6\nindicator("Test")\nvar int x = 0\nplot(close)'
            ast = PineAST(test_code)
            semantic = SemanticAnalyzer()
            scope = semantic.analyze(ast.root)
            return {
                'status': 'OK',
                'scopes': len(scope.children) + 1,
                'symbols': len(scope.symbols),
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
            return {
                'status': 'OK',
                'features_found': len(features),
                'detectors_active': 7,
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

    @classmethod
    def _check_storage(cls) -> Dict[str, Any]:
        knowledge_path = 'knowledge/bases/fixes'
        rules_path = 'knowledge/bases/rules'
        fixes_count = len([f for f in os.listdir(knowledge_path) if f.endswith('.yaml')]) if os.path.exists(knowledge_path) else 0
        return {
            'fixes_yaml': fixes_count,
            'rules_dir': os.path.exists(rules_path),
        }

    @classmethod
    def _calculate_overall(cls, results: Dict) -> str:
        statuses = []
        for key in ['parser', 'builtins', 'semantic', 'extractor']:
            if key in results:
                statuses.append(results[key].get('status', 'UNKNOWN'))

        if all(s == 'OK' for s in statuses):
            return 'HEALTHY ✅'
        elif any(s == 'ERROR' for s in statuses):
            return 'DEGRADED ⚠️'
        return 'UNKNOWN ❓'

    @classmethod
    def _get_memory_usage(cls) -> float:
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return round(process.memory_info().rss / 1024 / 1024, 2)
        except:
            return 0.0

    @classmethod
    def format_report(cls, health: Dict[str, Any]) -> str:
        """Format laporan kesehatan."""
        output = []
        output.append("╔══════════════════════════════════════════════╗")
        output.append(f"║  🏥 HEALTH CHECK: {health['overall_health']:<30} ║")
        output.append(f"║  🕐 {health['timestamp']}                    ║")
        output.append("╠══════════════════════════════════════════════╣")

        for key, value in health.items():
            if key in ('timestamp', 'overall_health'):
                continue
            if isinstance(value, dict):
                status = value.get('status', '?')
                icon = '✅' if status == 'OK' else '❌'
                output.append(f"║  {icon} {key.upper():<12} : {status:<10}                ║")
                for k, v in value.items():
                    if k != 'status' and k != 'error':
                        output.append(f"║     {k}: {v}")

        output.append("╚══════════════════════════════════════════════╝")
        return '\n'.join(output)
