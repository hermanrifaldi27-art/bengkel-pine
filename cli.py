#!/usr/bin/env python3
import sys
import argparse
import os
from engine.loader import RuleLoader
from engine.matcher import RuleMatcher
from engine.resolver import ParameterResolver
from engine.patch import PatchExecutor
from engine.verify import VerificationEngine
from engine.telemetry import load_telemetry, record_usage
from engine.parser import PineAST

def main():
    parser = argparse.ArgumentParser(description="BENGKEL-PINE Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    p_list = subparsers.add_parser("list", help="Tampilkan semua rules")
    p_tele = subparsers.add_parser("telemetry", help="Tampilkan statistik")
    p_repair = subparsers.add_parser("repair", help="Perbaiki file .pine")
    p_repair.add_argument("file", help="File .pine yang akan diperbaiki")
    p_repair.add_argument("--error", help="Pesan error dari kompiler (opsional)")
    p_repair.add_argument("--dry-run", action="store_true", help="Tampilkan hasil tanpa menulis file")
    p_extract = subparsers.add_parser("extract", help="Ekstrak pola dari file .pine ke YAML")
    p_extract.add_argument("file", help="File .pine yang akan diekstrak")
    
    args = parser.parse_args()
    
    if args.command == "list":
        loader = RuleLoader()
        rules = loader.load_all()
        print(f"\n📊 Total Rules: {len(rules)}")
        for err in loader.get_errors():
            print(f"⚠️ {err}")
        for r in rules:
            print(f"  - {r.get('id')} [{r.get('priority')}]")
    
    elif args.command == "telemetry":
        data = load_telemetry()
        if not data:
            print("📭 Belum ada data telemetry.")
        else:
            print("\n📊 TELEMETRY:")
            for rule_id, stats in data.items():
                success_rate = stats.get('success_count', 0) / max(stats.get('usage_count', 1), 1) * 100
                print(f"  - {rule_id}: {stats.get('usage_count',0)}x pakai, {success_rate:.1f}% sukses")
    
    elif args.command == "repair":
        file_path = args.file
        if not os.path.exists(file_path):
            print(f"❌ File tidak ditemukan: {file_path}")
            return
        
        with open(file_path, 'r') as f:
            user_code = f.read()
        
        ast = PineAST(user_code)
        context = {
            'symbols': ast.get_symbols(),
            'arrays': ast.get_arrays(),
            'matrices': ast.get_matrices(),
            'constants': ast.get_constants(),
            'functions': ast.functions,
            'ast': ast
        }
        
        print(f"🔍 AST: arrays={ast.get_arrays()}, matrices={ast.get_matrices()}")
        
        loader = RuleLoader()
        rules = loader.load_all()
        if not rules:
            print("❌ Tidak ada rule yang dimuat.")
            for err in loader.get_errors():
                print(f"   {err}")
            return
        
        matcher = RuleMatcher(rules)
        error_text = args.error or ""
        
        if error_text:
            matched = matcher.match_by_error(error_text)
            if not matched:
                matched = matcher.match_by_ast(ast)
        else:
            matched = matcher.match_by_ast(ast)
        
        if not matched:
            print("❌ Tidak ada rule yang cocok dengan kode ini.")
            return
        
        applied = False
        tried_ids = set()
        
        for rule in matched:
            rule_id = rule.get('id')
            if rule_id in tried_ids:
                continue
            tried_ids.add(rule_id)
            
            print(f"🔧 Mencoba rule: {rule_id}")
            
            resolver = ParameterResolver(context)
            resolved = resolver.resolve(rule)
            if resolved is None:
                print("   ❌ Gagal resolve parameter, skip.")
                continue
            print(f"   ✅ Resolved: {resolved}")
            
            patcher = PatchExecutor(user_code)
            patched_code = patcher.apply(rule, resolved)
            
            if patched_code == user_code:
                print("   ⚠️ Kode tidak berubah, skip.")
                record_usage(rule_id, False)
                continue
            
            verifier = VerificationEngine(user_code, patched_code)
            passed, msg = verifier.verify(rule, resolved)
            
            if passed:
                if args.dry_run:
                    print("   📄 [DRY RUN] Hasil perbaikan:")
                    print(patched_code[:500] + ("..." if len(patched_code) > 500 else ""))
                    print(f"   📋 {msg}")
                    applied = True
                    break
                output_path = file_path.replace('.pine', '_fixed.pine')
                with open(output_path, 'w') as f:
                    f.write(patched_code)
                print(f"✅ Kode berhasil diperbaiki! Output: {output_path}")
                print(f"📋 {msg}")
                record_usage(rule_id, True)
                applied = True
                break
            else:
                print(f"   ❌ {msg}")
                fallbacks = rule.get('fallbacks', [])
                if fallbacks:
                    for fb in fallbacks:
                        fb_id = fb.get('id') if isinstance(fb, dict) else fb
                        print(f"   🔄 Mencoba fallback: {fb_id}")
                        fb_rule = loader.get_by_id(fb_id)
                        if fb_rule:
                            # Re-run dengan fallback rule
                            fb_resolved = resolver.resolve(fb_rule)
                            if fb_resolved is not None:
                                fb_patched = patcher.apply(fb_rule, fb_resolved)
                                fb_verified, fb_msg = verifier.verify(fb_rule, fb_resolved)
                                if fb_verified:
                                    if args.dry_run:
                                        print(f"   📄 [DRY RUN] Fallback {fb_id} berhasil")
                                        applied = True
                                        break
                                    output_path = file_path.replace('.pine', '_fixed.pine')
                                    with open(output_path, 'w') as f:
                                        f.write(fb_patched)
                                    print(f"✅ Fallback {fb_id} berhasil! Output: {output_path}")
                                    print(f"📋 {fb_msg}")
                                    record_usage(fb_id, True)
                                    applied = True
                                    break
                record_usage(rule_id, False)
        
        if not applied:
            print("❌ Tidak ada rule yang berhasil memperbaiki kode.")
            sys.exit(1)
    
    elif args.command == "extract":
        from engine.extractor import extract_features
        extract_features(args.file)

if __name__ == "__main__":
    main()
