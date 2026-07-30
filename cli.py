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
    p_list.add_argument("--strict", action="store_true", help="Hanya rule actionable")

    p_tele = subparsers.add_parser("telemetry", help="Tampilkan statistik")

    p_repair = subparsers.add_parser("repair", help="Perbaiki file .pine")
    p_repair.add_argument("file", help="File .pine yang akan diperbaiki")
    p_repair.add_argument("--error", help="Pesan error dari kompiler (opsional)")
    p_repair.add_argument("--dry-run", action="store_true", help="Tampilkan hasil tanpa menulis file")
    p_repair.add_argument("--no-lint", action="store_true", help="Nonaktifkan linter otomatis")

    p_extract = subparsers.add_parser("extract", help="Ekstrak pola dari file .pine ke YAML")
    p_extract.add_argument("file", help="File .pine yang akan diekstrak")

    p_validate = subparsers.add_parser("validate", help="Validasi schema semua YAML rules (Pydantic-free)")
    p_validate.add_argument("--strict", action="store_true", help="Gagal jika ada non-actionable")

    p_lint = subparsers.add_parser("lint", help="Static lint file .pine (offline)")
    p_lint.add_argument("file", help="File .pine yang akan di-lint")

    args = parser.parse_args()

    if args.command == "list":
        loader = RuleLoader(strict=args.strict)
        rules = loader.load_all()
        print(f"\n📊 {loader.summary()}")
        for err in loader.get_errors()[:15]:
            print(f"⚠️ {err}")
        for w in loader.get_warnings()[:10]:
            print(f"  {w}")
        for r in rules:
            print(f"  - {r.get('id')} [{r.get('priority')}]")

    elif args.command == "telemetry":
        data = load_telemetry()
        if not data:
            print("📭 Belum ada data telemetry.")
        else:
            print("\n📊 TELEMETRY:")
            for rule_id, stats in data.items():
                success_rate = stats.get("success_count", 0) / max(stats.get("usage_count", 1), 1) * 100
                print(f"  - {rule_id}: {stats.get('usage_count',0)}x pakai, {success_rate:.1f}% sukses")

    elif args.command == "validate":
        loader = RuleLoader(strict=False)
        rules = loader.load_all()
        print(f"📊 {loader.summary()}")
        errs = loader.get_errors()
        if errs:
            print("\n── Issues ──")
            for e in errs:
                print(f"  {e}")
        actionable = [r for r in loader.validated_rules if r.is_actionable()]
        print(f"\n✅ Actionable rules: {len(actionable)}")
        for r in actionable:
            print(f"  - {r.id} [{r.priority.value}] op={r.action.operation.value}")
        if args.strict and errs:
            sys.exit(1)

    elif args.command == "lint":
        from engine.pine_linter import lint_file
        if not os.path.exists(args.file):
            print(f"❌ File tidak ditemukan: {args.file}")
            sys.exit(1)
        report = lint_file(args.file)
        print(report.format())
        if report.error_count:
            sys.exit(1)

    elif args.command == "repair":
        file_path = args.file
        if not os.path.exists(file_path):
            print(f"❌ File tidak ditemukan: {file_path}")
            return

        # 🔥 Linter otomatis (default ON, bisa dimatikan dengan --no-lint)
        if not args.no_lint:
            from engine.pine_linter import lint_file
            report = lint_file(file_path)
            print(report.format())

        with open(file_path, "r", encoding="utf-8") as f:
            user_code = f.read()

        ast = PineAST(user_code)
        context = {
            "symbols": ast.get_symbols(),
            "arrays": ast.get_arrays(),
            "matrices": ast.get_matrices(),
            "constants": ast.get_constants(),
            "functions": ast.functions,
            "ast": ast,
        }
        print(f"🔍 AST: arrays={ast.get_arrays()}, matrices={ast.get_matrices()}, constants={ast.get_constants()}")

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
            rule_id = rule.get("id")
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
                print("   ⚠️ Patch tidak mengubah kode, skip.")
                continue
            verifier = VerificationEngine(user_code, patched_code)
            passed, msg = verifier.verify(rule, resolved)
            if passed:
                if args.dry_run:
                    print("─── DRY-RUN OUTPUT ───")
                    print(patched_code)
                    print("─────────────────────")
                else:
                    output_path = file_path.replace(".pine", "_fixed.pine")
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(patched_code)
                    print(f"✅ Kode berhasil diperbaiki! Output: {output_path}")
                print(f"📋 {msg}")
                record_usage(rule_id, True)
                applied = True
                break
            else:
                print(f"   ❌ {msg}")
                record_usage(rule_id, False)
                fallbacks = rule.get("fallbacks", [])
                for fb in fallbacks:
                    fb_id = fb.get("id") if isinstance(fb, dict) else fb
                    if not fb_id or fb_id in tried_ids:
                        continue
                    print(f"   🔄 Mencoba fallback: {fb_id}")
                    fb_rule = loader.get_by_id(fb_id)
                    if not fb_rule:
                        continue
                    tried_ids.add(fb_id)
                    resolved_fb = resolver.resolve(fb_rule)
                    if resolved_fb is None:
                        continue
                    patched_fb = patcher.apply(fb_rule, resolved_fb)
                    if patched_fb == user_code:
                        continue
                    passed_fb, msg_fb = verifier.verify(fb_rule, resolved_fb)
                    if passed_fb:
                        if args.dry_run:
                            print("─── DRY-RUN (fallback) ───")
                            print(patched_fb)
                            print("─────────────────────────")
                        else:
                            output_path = file_path.replace(".pine", "_fixed.pine")
                            with open(output_path, "w", encoding="utf-8") as f:
                                f.write(patched_fb)
                            print(f"✅ Fallback berhasil! Output: {output_path}")
                        print(f"📋 {msg_fb}")
                        record_usage(fb_id, True)
                        applied = True
                        break
                    else:
                        record_usage(fb_id, False)
                if applied:
                    break

        if not applied:
            print("❌ Tidak ada rule yang berhasil memperbaiki kode.")
            sys.exit(1)

    elif args.command == "extract":
        from engine.extractor import extract_features
        extract_features(args.file)

if __name__ == "__main__":
    main()
