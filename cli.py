#!/usr/bin/env python3
"""
BENGKEL-PINE v2.0 — Auto-repair engine untuk Pine Script v6
"""
import sys
import argparse
import os
import logging
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

from engine.loader import RuleLoader
from engine.matcher import RuleMatcher
from engine.resolver import ParameterResolver
from engine.patch import PatchExecutor
from engine.verify import VerificationEngine
from engine.telemetry import load_telemetry, record_usage
from engine.parser import PineAST
from engine.pine_linter import lint_file
from engine.extractor import extract_features

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_ERROR_LENGTH = 2000
MAX_RULES_TO_TRY = 20
EXIT_ERROR = 1
EXIT_PARSE_ERROR = 2
EXIT_NO_RULE = 3
EXIT_IO_ERROR = 4
EXIT_SECURITY = 5

logger = logging.getLogger("bengkel_pine")

def setup_logging(quiet=False, verbose=False, log_file=None):
    level = logging.ERROR if quiet else (logging.DEBUG if verbose else logging.INFO)
    handlers = [logging.StreamHandler()]
    if log_file:
        try:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
        except OSError as e:
            print(f"Peringatan: Gagal buat log file: {e}", file=sys.stderr)
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s', handlers=handlers)

def is_safe_path(base_path, user_path):
    if os.path.isabs(user_path):
        return False
    base = os.path.realpath(base_path)
    user = os.path.realpath(os.path.join(base_path, user_path))
    try:
        return os.path.commonpath([base, user]) == base
    except ValueError:
        return False

def validate_input_file(file_path):
    p = Path(file_path)
    if p.suffix.lower() != '.pine':
        raise ValueError(f"File bukan .pine: {file_path}")
    if p.is_symlink():
        raise ValueError(f"Symlink tidak diizinkan: {file_path}")
    try:
        st = p.stat()
        if not stat.S_ISREG(st.st_mode):
            raise ValueError(f"Bukan regular file: {file_path}")
        if st.st_size > MAX_FILE_SIZE:
            raise ValueError(f"File terlalu besar: {st.st_size} bytes (max {MAX_FILE_SIZE})")
        return p
    except OSError as e:
        raise OSError(f"Gagal akses file: {e}")

def safe_read_file(file_path):
    try:
        return file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            return file_path.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError:
            raise ValueError("File harus UTF-8 atau UTF-8 BOM.")
    except OSError as e:
        raise OSError(f"Gagal membaca file: {e}")

def atomic_write(path, content, backup=False):
    if backup and path.exists():
        backup_path = path.with_suffix(path.suffix + '.bak')
        try:
            shutil.copy2(path, backup_path)
            logger.info(f"Backup ke {backup_path}")
        except OSError as e:
            raise OSError(f"Gagal backup: {e}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(suffix=".tmp", dir=path.parent, text=True)
    try:
        with os.fdopen(tmp_fd, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        if path.exists():
            st = path.stat()
            os.chmod(tmp_name, st.st_mode)
        os.replace(tmp_name, path)
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            logger.debug("Directory fsync dilewati")
    except OSError as e:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise OSError(f"Gagal menulis file: {e}")

_loader_cache = None
_loader_cache_key = None

def get_loader(strict=False):
    global _loader_cache, _loader_cache_key
    key = (strict,)
    if _loader_cache is not None and _loader_cache_key == key:
        return _loader_cache
    loader = RuleLoader(strict=strict)
    loader.load_all()
    _loader_cache = loader
    _loader_cache_key = key
    return loader

# ─── FUNGSI CLI BARU ───
def cmd_score(args):
    from engine.extractor import extract_features
    from engine.parser import PineAST
    from engine.scoring import ScoringEngine
    input_path = validate_input_file(args.file)
    code = safe_read_file(input_path)
    try:
        ast = PineAST(code)
    except Exception as e:
        logger.error(f"Gagal parsing AST: {e}")
        sys.exit(EXIT_PARSE_ERROR)
    features = extract_features(str(input_path)) or []
    report = ScoringEngine.calculate(features, code, ast.root)
    print(ScoringEngine.format_report(report))

def cmd_dashboard(args):
    from engine.extractor import extract_features
    from engine.parser import PineAST
    from engine.dashboard import Dashboard
    input_path = validate_input_file(args.file)
    code = safe_read_file(input_path)
    try:
        ast = PineAST(code)
    except Exception as e:
        logger.error(f"Gagal parsing AST: {e}")
        sys.exit(EXIT_PARSE_ERROR)
    features = extract_features(str(input_path)) or []
    print(Dashboard.generate(str(input_path), code, features, ast.root))

def cmd_health(args):
    from engine.health_check import HealthCheck
    health = HealthCheck.check_all()
    print(HealthCheck.format_report(health))

def cmd_audit(args):
    """Audit lengkap: scoring + best practice plugin + deduplikasi + health."""
    from engine.extractor import extract_features
    from engine.parser import PineAST
    from engine.scoring import ScoringEngine
    from engine.best_practice import BestPracticeOrchestrator
    from engine.deduplicator import Deduplicator
    from engine.health_check import HealthCheck

    input_path = validate_input_file(args.file)
    code = safe_read_file(input_path)

    try:
        ast = PineAST(code)
    except Exception as e:
        logger.error(f"Gagal parsing AST: {e}")
        sys.exit(EXIT_PARSE_ERROR)

    print(f"\n{'='*58}")
    print(f"  AUDIT LENGKAP: {args.file}")
    print(f"{'='*58}\n")

    # 1. Score
    features = extract_features(str(input_path)) or []
    report = ScoringEngine.calculate(features, code, ast.root)
    print(ScoringEngine.format_report(report))
    print()

    # 2. Best Practice
    orch = BestPracticeOrchestrator()
    orch.audit(ast.root, code)
    print(orch.format_report())
    print()

    # 3. Knowledge Base Health
    kb_report = Deduplicator.check_all()
    print(Deduplicator.format_report(kb_report))
    print()

    # 4. System Health
    health = HealthCheck.check_all()
    print(HealthCheck.format_report(health))


def cmd_fix(args):
    from engine.extractor import extract_features
    from engine.parser import PineAST
    from engine.auto_fixer import AutoFixer
    input_path = validate_input_file(args.file)
    code = safe_read_file(input_path)
    try:
        ast = PineAST(code)
    except Exception as e:
        logger.error(f"Gagal parsing AST: {e}")
        sys.exit(EXIT_PARSE_ERROR)
    features = extract_features(str(input_path)) or []
    if not features:
        print("Tidak ada masalah yang perlu diperbaiki.")
        return
    print(f"Ditemukan {len(features)} masalah:")
    for f in features:
        print(f"   - {f.goal}")
    result = AutoFixer.fix(
        str(input_path), features, code,
        dry_run=not args.apply,
        auto_confirm=args.auto_confirm
    )
    if result and not args.apply:
        print("")
        print("Gunakan --apply untuk menerapkan perbaikan.")

# ─── MAIN ───
def main():
    parser = argparse.ArgumentParser(description="BENGKEL-PINE Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_list = subparsers.add_parser("list", help="Tampilkan semua rules")
    p_list.add_argument("--strict", action="store_true", help="Hanya rule actionable")
    subparsers.add_parser("telemetry", help="Tampilkan statistik")

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

    p_validate = subparsers.add_parser("validate", help="Validasi schema semua YAML rules")
    p_validate.add_argument("--strict", action="store_true", help="Gagal jika ada non-actionable")

    p_lint = subparsers.add_parser("lint", help="Static lint file .pine (offline)")
    p_lint.add_argument("file", help="File .pine yang akan di-lint")

    p_score = subparsers.add_parser("score", help="Skor kualitas file .pine")
    p_score.add_argument("file", help="File .pine yang akan dinilai")

    p_dashboard = subparsers.add_parser("dashboard", help="Dashboard lengkap file .pine")
    p_dashboard.add_argument("file", help="File .pine yang akan dianalisis")

    p_health = subparsers.add_parser("health", help="Periksa kesehatan sistem")

    p_audit = subparsers.add_parser("audit", help="Audit lengkap: masalah + best practice + dedup")
    p_audit.add_argument("file", help="File .pine yang akan diaudit")

    p_fix = subparsers.add_parser("fix", help="Perbaiki otomatis file .pine")
    p_fix.add_argument("file", help="File .pine yang akan diperbaiki")
    p_fix.add_argument("--apply", action="store_true", help="Terapkan perbaikan")
    p_fix.add_argument("--auto-confirm", action="store_true", help="Setujui semua perbaikan")

    args = parser.parse_args()
    log_file = os.environ.get('PINE_LOG_FILE')
    setup_logging(quiet=getattr(args, 'quiet', False), verbose=getattr(args, 'verbose', False), log_file=log_file)

    if args.command == "list":
        loader = get_loader(strict=args.strict)
        print(f"\n{loader.summary()}")
        for r in loader.rules:
            print(f"  - {r.get('id')} [{r.get('priority')}]")
        return

    if args.command == "telemetry":
        data = load_telemetry()
        if not data:
            print("Belum ada data telemetry.")
        else:
            print("\nTELEMETRY:")
            for rule_id, stats in data.items():
                success_rate = stats.get("success_count", 0) / max(stats.get("usage_count", 1), 1) * 100
                print(f"  - {rule_id}: {stats.get('usage_count',0)}x pakai, {success_rate:.1f}% sukses")
        return

    if args.command == "validate":
        loader = get_loader(strict=False)
        print(f"{loader.summary()}")
        errs = loader.get_errors()
        if errs:
            print("\nIssues:")
            for e in errs:
                logger.warning(e)
        actionable = [r for r in loader.validated_rules if r.is_actionable()]
        print(f"\nActionable rules: {len(actionable)}")
        for r in actionable:
            print(f"  - {r.id} [{r.priority.value}] op={r.action.operation.value}")
        if args.strict and errs:
            sys.exit(EXIT_ERROR)
        return

    if args.command == "lint":
        input_path = validate_input_file(args.file)
        try:
            report = lint_file(str(input_path))
        except Exception as e:
            logger.error(f"Lint gagal: {e}")
            sys.exit(EXIT_ERROR)
        print(report.format())
        if report.error_count:
            sys.exit(EXIT_ERROR)
        return

    if args.command == "extract":
        input_path = validate_input_file(args.file)
        try:
            extract_features(str(input_path))
        except Exception as e:
            logger.error(f"Extract gagal: {e}")
            sys.exit(EXIT_ERROR)
        return

    if args.command == "score":
        cmd_score(args)
        return

    if args.command == "dashboard":
        cmd_dashboard(args)
        return

    if args.command == "health":
        cmd_health(args)
        return

    if args.command == "audit":
        cmd_audit(args)
        return

    if args.command == "fix":
        cmd_fix(args)
        return

    if args.command == "repair":
        input_path = validate_input_file(args.file)
        if not args.no_lint:
            try:
                report = lint_file(str(input_path))
            except Exception as e:
                logger.error(f"Lint gagal: {e}")
                sys.exit(EXIT_ERROR)
            print(report.format())
        user_code = safe_read_file(input_path)
        try:
            ast = PineAST(user_code)
        except Exception as e:
            logger.error(f"Gagal parsing AST: {e}")
            sys.exit(EXIT_PARSE_ERROR)
        symbols = ast.get_symbols()
        arrays = ast.get_arrays()
        matrices = ast.get_matrices()
        constants = ast.get_constants()
        functions = ast.functions
        context = {"symbols": symbols, "arrays": arrays, "matrices": matrices, "constants": constants, "functions": functions, "ast": ast}
        loader = get_loader()
        if not loader.rules:
            logger.error("Tidak ada rule yang dimuat.")
            sys.exit(EXIT_ERROR)
        matcher = RuleMatcher(loader.rules)
        error_text = ""
        if args.error:
            error_text = args.error.replace('\n', ' ').replace('\r', ' ')[:MAX_ERROR_LENGTH]
        if error_text:
            matched = matcher.match(error_text=error_text, ast=ast, strategy="intersect")
            if not matched and getattr(args, 'force_union', False):
                matched = matcher.match(ast=ast, strategy="union")
        else:
            matched = matcher.match(ast=ast, strategy="union")
        if not matched:
            logger.warning("Tidak ada rule yang cocok dengan kode ini.")
            sys.exit(EXIT_NO_RULE)
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.with_stem(input_path.stem + '_fixed')
        if not args.dry_run:
            if output_path.resolve(strict=False) == input_path.resolve(strict=False):
                logger.error("Output path sama dengan input. Gunakan --output.")
                sys.exit(EXIT_ERROR)
        if len(matched) > MAX_RULES_TO_TRY:
            matched = matched[:MAX_RULES_TO_TRY]
        resolver = ParameterResolver(context)
        applied = False
        for rule in matched:
            rule_id = rule.get("id")
            if not rule_id:
                continue
            logger.info(f"Mencoba rule: {rule_id}")
            try:
                resolved = resolver.resolve(rule)
            except Exception as e:
                logger.warning(f"Resolve error: {e}")
                continue
            if resolved is None:
                logger.warning("Gagal resolve parameter")
                continue
            try:
                patcher = PatchExecutor(user_code, context)
                patched = patcher.apply(rule, resolved)
            except Exception as e:
                logger.warning(f"Patch error: {e}")
                continue
            if patched == user_code:
                continue
            try:
                verifier = VerificationEngine(user_code, patched, context)
                passed, msg = verifier.verify(rule, resolved)
            except Exception as e:
                passed = False
                msg = str(e)
            try:
                record_usage(rule_id, passed)
            except Exception as e:
                logger.warning(f"Telemetry error: {e}")
            if passed:
                if args.dry_run:
                    print("--- DRY-RUN OUTPUT ---")
                    print(patched)
                    print("---------------------")
                else:
                    if output_path.exists() and not args.force:
                        logger.error(f"File output '{output_path}' sudah ada.")
                        sys.exit(EXIT_IO_ERROR)
                    try:
                        atomic_write(output_path, patched, backup=args.backup)
                    except OSError as e:
                        logger.error(str(e))
                        sys.exit(EXIT_IO_ERROR)
                    logger.info(f"Kode berhasil diperbaiki! Output: {output_path}")
                applied = True
                break
        if not applied:
            logger.error("Tidak ada rule yang berhasil memperbaiki kode.")
            sys.exit(EXIT_ERROR)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDibatalkan oleh pengguna")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Kesalahan tak terduga: {e}")
        sys.exit(EXIT_ERROR)
