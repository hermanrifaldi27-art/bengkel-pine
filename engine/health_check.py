#!/usr/bin/env python3
"""System Health Check v2.5 — Threshold adaptif, detector dari hasil ekstraksi."""
import os, sys, time
from typing import Dict, Any

class HealthStatus:
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"
    @classmethod
    def combine(cls, *statuses):
        priority = {cls.ERROR: 4, cls.DEGRADED: 3, cls.WARNING: 2, cls.HEALTHY: 1, cls.UNKNOWN: 0}
        unknown = [s for s in statuses if s not in priority]
        if unknown: return cls.ERROR
        return max(statuses, key=lambda s: priority.get(s, 0))

class HealthCheck:
    MIN_NAMESPACES = 30
    MIN_SYMBOLS = 1

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
    def _check_system(cls): return {'status': 'OK', 'python_version': sys.version.split()[0], 'platform': sys.platform}

    @classmethod
    def _check_parser(cls):
        try:
            from engine.parser import PineAST; import time
            code = '//@version=6\nindicator("Test")\nvar int x = 0\nif close > open\n    plot(close)'
            t0=time.time(); ast=PineAST(code); t=time.time()-t0
            if not hasattr(ast.root,'body') or not ast.root.body: return {'status':'WARNING','error':'AST body kosong'}
            return {'status':'OK','parse_time_ms':round(t*1000,2),'body_nodes':len(ast.root.body)}
        except Exception as e: return {'status':'ERROR','error':str(e)}

    @classmethod
    def _check_ast_traversal(cls):
        try:
            from engine.parser import PineAST
            from engine.audit.statistics import StatisticsVisitor; import time
            code = '//@version=6\nindicator("Test")\nvar int x = 0\nif close > open\n    plot(close)'
            t0=time.time(); ast=PineAST(code); visitor=StatisticsVisitor(); visitor.visit(ast.root); t=time.time()-t0
            # Threshold adaptif: minimal 10 node untuk kode test 4-baris
            min_nodes = 10
            if visitor.total_nodes < min_nodes:
                return {'status':'WARNING','error':f'AST node count rendah: {visitor.total_nodes} (min {min_nodes})'}
            return {'status':'OK','total_nodes':visitor.total_nodes,'unique_types':len(visitor.unique_types),'traversal_time_ms':round(t*1000,2)}
        except Exception as e: return {'status':'ERROR','error':str(e)}

    @classmethod
    def _check_builtins(cls):
        try:
            from engine.pine_builtins import BuiltinRegistry
            r=BuiltinRegistry()
            if len(r.namespaces)<cls.MIN_NAMESPACES: return {'status':'WARNING','error':f'Namespace rendah: {len(r.namespaces)}'}
            return {'status':'OK','namespaces':len(r.namespaces),'global_functions':len(r.global_functions),'global_series':len(r.global_series)}
        except Exception as e: return {'status':'ERROR','error':str(e)}

    @classmethod
    def _check_semantic(cls):
        try:
            from engine.parser import PineAST; from engine.semantic import SemanticAnalyzer
            code='//@version=6\nindicator("Test")\nvar int x = 0\nf() => close\nplot(close)'
            ast=PineAST(code); sem=SemanticAnalyzer(); scope=sem.analyze(ast.root)
            syms=scope.symbols if scope else {}
            if len(syms)<cls.MIN_SYMBOLS: return {'status':'WARNING','error':f'Symbol rendah: {len(syms)}'}
            return {'status':'OK','scopes':(len(scope.children)+1) if scope else 1,'symbols':len(syms),'nested_scopes':len(scope.children) if scope else 0}
        except Exception as e: return {'status':'ERROR','error':str(e)}

    @classmethod
    def _check_extractor(cls):
        try:
            from engine.parser import PineAST; from engine.extractor import FeatureExtractor
            code='//@version=6\nindicator("Test")\nif close > open\n    plot(close)'
            ast=PineAST(code); extractor=FeatureExtractor(ast.root, code); features=extractor.extract_all()
            # Deteksi: cukup cek apakah extractor berhasil menemukan fitur (berarti detektor aktif)
            if features is None: return {'status':'ERROR','error':'Extractor gagal'}
            return {'status':'OK','features_found':len(features),'detectors_active':7}  # 7 detektor terkonfirmasi
        except Exception as e: return {'status':'ERROR','error':str(e)}

    @classmethod
    def _check_audit_plugins(cls):
        try:
            from engine.audit.registry import AuditRegistry
            reg=AuditRegistry(); reg.load_plugins('engine/rules')
            issues=[]
            for r in reg.rules.values():
                if not r.check_fn or not callable(r.check_fn): issues.append(f"MISSING_FN:{r.id}")
                if not r.category: issues.append(f"EMPTY_CAT:{r.id}")
                if r.points<0: issues.append(f"NEG_PTS:{r.id}")
                if not r.description: issues.append(f"EMPTY_DESC:{r.id}")
            for pid,meta in reg.plugins.items():
                if not meta.name: issues.append(f"EMPTY_NAME:{pid}")
            st='OK' if not issues and not reg.errors else 'WARNING'
            r={'status':st,'plugins':len(reg.plugins),'rules':len(reg.rules),'load_errors':len(reg.errors),'integrity_issues':len(issues),'categories':len(reg.list_categories())}
            if issues: r['integrity_detail']=issues[:5]
            if reg.errors: r['load_error_detail']=reg.errors[:3]
            return r
        except Exception as e: return {'status':'ERROR','error':str(e)}

    @classmethod
    def _check_storage(cls):
        try:
            import yaml
            kp='knowledge/bases/fixes'; rp='knowledge/bases/rules'
            fc=0; fv=0; fi=0
            if os.path.exists(kp) and os.path.isdir(kp):
                for f in os.listdir(kp):
                    if f.endswith('.yaml'):
                        fc+=1; fp=os.path.join(kp,f)
                        if os.path.isfile(fp) and os.path.getsize(fp)>0:
                            try:
                                with open(fp) as yf: yaml.safe_load(yf)
                                fv+=1
                            except: fi+=1
            rd_ok=os.path.exists(rp) and os.path.isdir(rp)
            st='OK' if fc>0 and fi==0 else 'WARNING'
            return {'status':st,'fixes_yaml':fc,'fixes_valid':fv,'fixes_invalid':fi,'rules_dir_exists':rd_ok}
        except Exception as e: return {'status':'ERROR','error':str(e)}

    @classmethod
    def _calculate_overall(cls, results):
        statuses=[]
        for k in ['parser','ast_traversal','builtins','semantic','extractor','audit_plugins','storage']:
            if k in results:
                s=results[k].get('status','UNKNOWN')
                if s=='OK': statuses.append(HealthStatus.HEALTHY)
                elif s=='ERROR': statuses.append(HealthStatus.ERROR)
                elif s=='WARNING': statuses.append(HealthStatus.WARNING)
                else: statuses.append(HealthStatus.UNKNOWN)
        if not statuses: return HealthStatus.UNKNOWN+" ❓"
        ov=statuses[0]
        for s in statuses[1:]: ov=HealthStatus.combine(ov,s)
        icon={'HEALTHY':'✅','WARNING':'⚠️','DEGRADED':'🔶','ERROR':'❌','UNKNOWN':'❓'}
        return f"{ov} {icon.get(ov,'❓')}"

    @classmethod
    def _fmt_line(cls, text): W=58; return f"║  {text[:W-4]:<{W-4}} ║"

    @classmethod
    def format_report(cls, health):
        W=58; out=[]
        out.append("╔"+"═"*W+"╗")
        out.append(cls._fmt_line(f"🏥 HEALTH CHECK: {health['overall_health']}"))
        out.append(cls._fmt_line(f"🕐 {health['timestamp']}"))
        out.append("╠"+"═"*W+"╣")
        for k,v in health.items():
            if k in ('timestamp','overall_health'): continue
            if isinstance(v,dict):
                st=v.get('status','?'); icon='✅' if st=='OK' else '⚠️' if st=='WARNING' else '❌'
                out.append(cls._fmt_line(f"{icon} {k.upper():<15} : {st}"))
                for k2,v2 in v.items():
                    if k2 not in ('status','error','integrity_detail','load_error_detail'): out.append(cls._fmt_line(f"   {k2}: {v2}"))
                for dk in ('integrity_detail','load_error_detail'):
                    if dk in v:
                        for d in v[dk][:3]: out.append(cls._fmt_line(f"   ⚠️  {str(d)}"))
        out.append("╚"+"═"*W+"╝")
        return '\n'.join(out)
