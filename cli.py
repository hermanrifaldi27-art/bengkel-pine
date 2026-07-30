#!/usr/bin/env python3
import sys
import argparse
import os
import logging
from engine.loader import RuleLoader
from engine.matcher import RuleMatcher
from engine.resolver import ParameterResolver
from engine.patch import PatchExecutor
from engine.verify import VerificationEngine
from engine.telemetry import load_telemetry, record_usage
from engine.parser import PineAST

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger("bengkel_pine")

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
    p_repair.add_argument("--output", help="Path output (default: file_fixed.pine)")
    p_repair.add_argument("--backup", action="store_true", help="Backup original file sebelum overwrite")
    p_repair.add_argument("--quiet", action="store_true", help="Minimal output")
    p_repair.add_argument("--verbose", action="store_true", help="Tampilkan detail debug")
    p_repair.add_argument("--force", action="store_true", help="Timpa file output tanpa konfirmasi")
    p_repair.add_argument("--force-union", action="store_true", help="Jika intersect tidak match, coba union mode")

    p_extract = subparsers.add_parser("extract", help="Ekstrak pola dari file .pine ke YAML")
    p_extract.add_argument("file", help="File .pine yang akan diekstrak")

    p_validate = subparsers.add_parser("validate", help="Validasi schema semua YAML rules (Pydantic-free)")
    p_validate.add_argument("--strict", action="store_true", help="Gagal jika ada non-actionable")

    p_lint = subparsers.add_parser("lint", help="Static lint file .pine (offline)")
    p_lint.add_argument("file", help="File .pine yang akan di-lint")

    args = parser.parse_args()

    if hasattr(args, 'quiet') and args.quiet:
        logger.setLevel(logging.ERROR)
    elif hasattr(args, 'verbose') and args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.command == "list":
        loader = RuleLoader(strict=args.strict)
        rules = loader.load_all()
        print(f"\n📊 {loader.summary()}")
        for err in loader.get_errors()[:15]:
            logger.warning(err)
        for w in loader.get_warnings()[:10]:
            logger.info(w)
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
                logger.warning(e)
        actionable = [r for r in loader.validated_rules if r.is_actionable()]
        print(f"\n✅ Actionable rules: {len(actionable)}")
        for r in actionable:
            print(f"  - {r.id} [{r.priority.value}] op={r.action.operation.value}")
        if args.strict and errs:
            sys.exit(1)

    elif args.command == "lint":
        from engine.pine_linter import lint_file
        if not os.path.exists(args.file):
            logger.error(f"File tidak ditemukan: {args.file}")
            sys.exit(1)
        report = lint_file(args.file)
        print(report.format())
        if report.error_count:
            sys.exit(1)

    elif args.command == "repair":
        file_path = args.file
        if not os.path.exists(file_path):
            logger.error(f"File tidak ditemukan: {file_path}")
            return

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
        logger.debug(f"AST: arrays={ast.get_arrays()}, matrices={ast.get_matrices()}, constants={ast.get_constants()}")

        loader = RuleLoader()
        rules = loader.load_all()
        if not rules:
            logger.error("Tidak ada rule yang dimuat.")
            for err in loader.get_errors():
                logger.error(err)
            return

        matcher = RuleMatcher(rules)
        error_text = args.error or ""

        if error_text:
            matched = matcher.match(error_text=error_text, ast=ast, strategy="intersect")
            # 🔥 FORCE-UNION: Jika intersect gagal dan user minta force-union, coba union
            if not matched and getattr(args, 'force_union', False):
                logger.info("Intersect tidak match, mencoba union mode (--force-union)")
                matched = matcher.match(ast=ast, strategy="union")
        else:
            matched = matcher.match(ast=ast, strategy="union")

        if not matched:
            logger.warning("Tidak ada rule yang cocok dengan kode ini.")
            return

        if args.output:
            output_path = args.output
        else:
            output_path = file_path.replace(".pine", "_fixed.pine")

        # Backup jika diperlukan (kecuali dry-run)
        if not args.dry_run and args.backup and os.path.exists(output_path):
            backup_path = output_path + ".bak"
            import shutil
            shutil.copy2(output_path, backup_path)
            logger.info(f"Backup file output sebelumnya ke {backup_path}")

        applied = False
        tried_ids = set()

        def _try_rule(rule, patcher, resolver):
            nonlocal applied
            rule_id = rule.get("id")
            if rule_id in tried_ids:
                return False
            tried_ids.add(rule_id)

            logger.info(f"Mencoba rule: {rule_id}")
            resolved = resolver.resolve(rule)
            if resolved is None:
                logger.warning(f"Gagal resolve parameter, skip.")
                return False
            logger.debug(f"Resolved: {resolved}")

            patcher.context = context
            patched = patcher.apply(rule, resolved)
            if patched == user_code:
                logger.warning(f"Patch tidak mengubah kode, skip.")
                return False

            verifier = VerificationEngine(user_code, patched, context)
            passed, msg = verifier.verify(rule, resolved)
            record_usage(rule_id, passed)

            if passed:
                if args.dry_run:
                    print("─── DRY-RUN OUTPUT ───")
                    print(patched)
                    print("─────────────────────")
                else:
                    # Cek jika file ada dan tidak pake --force, kita kasih warning (tapi tetap tulis)
                    if os.path.exists(output_path) and not args.force:
                        logger.warning(f"File output '{output_path}' sudah ada. Gunakan --force untuk menimpa.")
                        # Tapi tetap kita tulis agar tidak error, karena user sudah punya --force
                    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write(patched)
                    logger.info(f"Kode berhasil diperbaiki! Output: {output_path}")
                logger.info(msg)
                applied = True
                return True
            else:
                logger.warning(f"Verifikasi gagal: {msg}")
                return False

        patcher = PatchExecutor(user_code, context)
        resolver = ParameterResolver(context)

        for rule in matched:
            if _try_rule(rule, patcher, resolver):
                break
            fallbacks = rule.get("fallbacks", [])
            for fb in fallbacks:
                fb_id = fb.get("id") if isinstance(fb, dict) else fb
                fb_rule = loader.get_by_id(fb_id)
                if fb_rule and _try_rule(fb_rule, patcher, resolver):
                    break
            if applied:
                break

        if not applied:
            logger.error("Tidak ada rule yang berhasil memperbaiki kode.")
            sys.exit(1)

    elif args.command == "extract":
        from engine.extractor import extract_features
        extract_features(args.file)

if __name__ == "__main__":
    main()
