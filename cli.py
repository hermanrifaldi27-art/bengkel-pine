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
        
        loader = RuleLoader()
        rules = loader.load_all()
        if not rules:
            print("❌ Tidak ada rule yang dimuat.")
            return
        
        error_text = args.error or ""
        matcher = RuleMatcher(rules)
        if error_text:
            matched = matcher.match_by_error(error_text)
            if not matched:
                matched = rules
        else:
            matched = rules
        
        applied = False
        for rule in matched:
            print(f"🔧 Mencoba rule: {rule.get('id')}")
            
            resolver = ParameterResolver(context)
            resolved = resolver.resolve(rule)
            if resolved is None:
                print("   ❌ Gagal resolve parameter, skip.")
                continue
            print(f"   ✅ Resolved: {resolved}")
            
            patcher = PatchExecutor(user_code)
            patched_code = patcher.apply(rule, resolved)
            
            verifier = VerificationEngine(user_code, patched_code)
            passed, msg = verifier.verify(rule, resolved)
            
            if passed:
                output_path = file_path.replace('.pine', '_fixed.pine')
                with open(output_path, 'w') as f:
                    f.write(patched_code)
                print(f"✅ Kode berhasil diperbaiki! Output: {output_path}")
                print(f"📋 {msg}")
                record_usage(rule.get('id'), True)
                applied = True
                break
            else:
                print(f"   ❌ {msg}")
                fallbacks = rule.get('fallbacks', [])
                if fallbacks:
                    print(f"   🔄 Mencoba fallback: {fallbacks[0].get('id')}")
                record_usage(rule.get('id'), False)
        
        if not applied:
            print("❌ Tidak ada rule yang berhasil memperbaiki kode.")
            sys.exit(1)
    
    elif args.command == "extract":
        # 🔥 Import hanya di sini, saat perintah extract dijalankan
        from engine.extractor import extract_features
        extract_features(args.file)

if __name__ == "__main__":
    main()
