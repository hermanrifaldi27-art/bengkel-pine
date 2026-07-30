#!/usr/bin/env python3
"""
BENGKEL-PINE v1.0 — Auto-repair engine untuk Pine Script v6
CLI final: fsync direktori non‑fatal, helper raise exception, sorting assumption documented
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

# ─── CONSTANTS ──────────────────────────────────────────────────────
MAX_FILE_SIZE = 10 * 1024 * 1024       # 10 MB
MAX_ERROR_LENGTH = 2000                # untuk sanitasi error
MAX_RULES_TO_TRY = 20                  # top‑N (asumsi matcher sudah sorting)

EXIT_ERROR = 1
EXIT_PARSE_ERROR = 2
EXIT_NO_RULE = 3
EXIT_IO_ERROR = 4
EXIT_SECURITY = 5

# ─── LOGGING ────────────────────────────────────────────────────────
logger = logging.getLogger("bengkel_pine")

def setup_logging(quiet: bool = False, verbose: bool = False, log_file: Optional[str] = None):
    level = logging.ERROR if quiet else (logging.DEBUG if verbose else logging.INFO)
    handlers = [logging.StreamHandler()]
    if log_file:
        try:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
        except OSError as e:
            print(f"⚠️  Peringatan: Gagal buat log file '{log_file}': {e}", file=sys.stderr)
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s',
        handlers=handlers
    )

# ─── SAFETY: File validation ──────────────────────────────────────
def is_safe_path(base_path: str, user_path: str) -> bool:
    """Cegah path traversal dan absolute path"""
    if os.path.isabs(user_path):
        return False
    base = os.path.realpath(base_path)
    user = os.path.realpath(os.path.join(base_path, user_path))
    try:
        return os.path.commonpath([base, user]) == base
    except ValueError:
        return False

def validate_input_file(file_path: str) -> Path:
    """
    Validasi file input: ekstensi, regular file, ukuran, symlink, FIFO.
    Raises: OSError, ValueError
    """
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

def safe_read_file(file_path: Path) -> str:
    """Baca file dengan encoding UTF-8 deterministik (fallback hanya UTF-8-SIG)"""
    try:
        return file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            return file_path.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError:
            raise ValueError("File harus UTF-8 atau UTF-8 BOM.")
    except OSError as e:
        raise OSError(f"Gagal membaca file: {e}")

# ─── ATOMIC WRITE ──────────────────────────────────────────────────
def atomic_write(path: Path, content: str, backup: bool = False) -> None:
    """Tulis file secara atomic, fsync file + direktori (non‑fatal)"""
    if backup and path.exists():
        backup_path = path.with_suffix(path.suffix + '.bak')
        try:
            shutil.copy2(path, backup_path)
            logger.info(f"Backup ke {backup_path}")
        except OSError as e:
            raise OSError(f"Gagal backup: {e}")

    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_fd, tmp_name = tempfile.mkstemp(
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    try:
        with os.fdopen(tmp_fd, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        if path.exists():
            st = path.stat()
            os.chmod(tmp_name, st.st_mode)

        os.replace(tmp_name, path)

        # 🔥 fsync direktori (non‑fatal)
        try:
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError as e:
            logger.debug(f"Directory fsync dilewati: {e}")

    except OSError as e:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise OSError(f"Gagal menulis file: {e}")

# ─── LOADER CACHE ──────────────────────────────────────────────────
_loader_cache = None
_loader_cache_key = None

def get_loader(strict: bool = False) -> RuleLoader:
    global _loader_cache, _loader_cache_key
    key = (strict,)
    if _loader_cache is not None and _loader_cache_key == key:
        return _loader_cache
    loader = RuleLoader(strict=strict)
    loader.load_all()
    _loader_cache = loader
    _loader_cache_key = key
    return loader

# ─── MAIN ──────────────────────────────────────────────────────────
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

    args = parser.parse_args()

    log_file = os.environ.get('PINE_LOG_FILE')
    setup_logging(
        quiet=getattr(args, 'quiet', False),
        verbose=getattr(args, 'verbose', False),
        log_file=log_file
    )

    # ── wrapper untuk menangkap exception dari helper ──
    def safe_call(func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (OSError, ValueError) as e:
            logger.error(str(e))
            sys.exit(EXIT_IO_ERROR if isinstance(e, OSError) else EXIT_ERROR)
        except Exception as e:
            logger.error(f"Kesalahan tak terduga: {e}")
            sys.exit(EXIT_ERROR)

    # ── list ──
    if args.command == "list":
        loader = get_loader(strict=args.strict)
        print(f"\n📊 {loader.summary()}")
        for err in loader.get_errors()[:15]:
            logger.warning(err)
        for w in loader.get_warnings()[:10]:
            logger.info(w)
        for r in loader.rules:
            print(f"  - {r.get('id')} [{r.get('priority')}]")
        return

    # ── telemetry ──
    if args.command == "telemetry":
        data = load_telemetry()
        if not data:
            print("📭 Belum ada data telemetry.")
        else:
            print("\n📊 TELEMETRY:")
            for rule_id, stats in data.items():
                success_rate = stats.get("success_count", 0) / max(stats.get("usage_count", 1), 1) * 100
                print(f"  - {rule_id}: {stats.get('usage_count',0)}x pakai, {success_rate:.1f}% sukses")
        return

    # ── validate ──
    if args.command == "validate":
        loader = get_loader(strict=False)
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
            sys.exit(EXIT_ERROR)
        return

    # ── lint ──
    if args.command == "lint":
        input_path = safe_call(validate_input_file, args.file)
        try:
            report = lint_file(str(input_path))
        except Exception as e:
            logger.error(f"Lint gagal: {e}")
            sys.exit(EXIT_ERROR)
        print(report.format())
        if report.error_count:
            sys.exit(EXIT_ERROR)
        return

    # ── extract ──
    if args.command == "extract":
        input_path = safe_call(validate_input_file, args.file)
        try:
            extract_features(str(input_path))
        except Exception as e:
            logger.error(f"Extract gagal: {e}")
            sys.exit(EXIT_ERROR)
        return

    # ── repair ──
    if args.command == "repair":
        # 1. Validasi input
        input_path = safe_call(validate_input_file, args.file)

        # 2. Linter
        if not args.no_lint:
            try:
                report = lint_file(str(input_path))
            except Exception as e:
                logger.error(f"Lint gagal: {e}")
                sys.exit(EXIT_ERROR)
            print(report.format())

        # 3. Baca file
        user_code = safe_call(safe_read_file, input_path)

        # 4. Parse AST
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

        context = {
            "symbols": symbols,
            "arrays": arrays,
            "matrices": matrices,
            "constants": constants,
            "functions": functions,
            "ast": ast,
        }
        logger.debug(f"AST: {len(arrays)} arrays, {len(matrices)} matrices, {len(constants)} constants")

        # 5. Load rules
        loader = get_loader()
        if not loader.rules:
            logger.error("Tidak ada rule yang dimuat.")
            for err in loader.get_errors():
                logger.error(err)
            sys.exit(EXIT_ERROR)

        # 6. Match
        matcher = RuleMatcher(loader.rules)
        error_text = ""
        if args.error:
            error_text = args.error.replace('\n', ' ').replace('\r', ' ')[:MAX_ERROR_LENGTH]

        if error_text:
            matched = matcher.match(error_text=error_text, ast=ast, strategy="intersect")
            if not matched and getattr(args, 'force_union', False):
                logger.info("Intersect tidak match, mencoba union mode (--force-union)")
                matched = matcher.match(ast=ast, strategy="union")
        else:
            matched = matcher.match(ast=ast, strategy="union")

        if not matched:
            logger.warning("Tidak ada rule yang cocok dengan kode ini.")
            sys.exit(EXIT_NO_RULE)

        # 7. Tentukan output path
        if args.output:
            output_path = Path(args.output)
            if output_path.suffix.lower() != '.pine':
                logger.warning(f"Output '{output_path}' bukan .pine. Engine tetap menulis, pastikan sesuai.")
        else:
            output_path = input_path.with_stem(input_path.stem + '_fixed')
            if output_path.suffix.lower() != '.pine':
                output_path = output_path.with_suffix('.pine')

        # 8. Security
        if not is_safe_path(os.getcwd(), str(output_path)):
            logger.error("⚠️ Path traversal detected! Output path tidak aman.")
            sys.exit(EXIT_SECURITY)

        # 9. Cegah output == input
        if not args.dry_run:
            if output_path.resolve(strict=False) == input_path.resolve(strict=False):
                logger.error("Output path sama dengan input. Gunakan --output untuk menentukan nama lain.")
                sys.exit(EXIT_ERROR)

        # 10. Batasi rule
        if len(matched) > MAX_RULES_TO_TRY:
            logger.info(f"Terlalu banyak rule match ({len(matched)}), hanya {MAX_RULES_TO_TRY} pertama yang dicoba")
            matched = matched[:MAX_RULES_TO_TRY]

        # 11. Patch
        resolver = ParameterResolver(context)
        applied = False
        tried_ids = set()

        def try_rule(rule: Dict[str, Any]) -> bool:
            nonlocal applied
            rule_id = rule.get("id")
            if not rule_id:
                logger.warning("Rule tanpa id, dilewati.")
                return False
            if rule_id in tried_ids:
                return False
            tried_ids.add(rule_id)

            logger.info(f"Mencoba rule: {rule_id}")
            try:
                resolved = resolver.resolve(rule)
            except Exception as e:
                logger.warning(f"Resolve error: {e}")
                return False

            if resolved is None:
                logger.warning("Gagal resolve parameter, skip.")
                return False
            logger.debug(f"Resolved: {resolved}")

            try:
                patcher = PatchExecutor(user_code, context)
                patched = patcher.apply(rule, resolved)
            except Exception as e:
                logger.warning(f"Patch error: {e}")
                return False

            if patched == user_code:
                logger.warning("Patch tidak mengubah kode, skip.")
                return False

            try:
                verifier = VerificationEngine(user_code, patched, context)
            except Exception as e:
                logger.warning(f"Verifier init error: {e}")
                return False

            try:
                passed, msg = verifier.verify(rule, resolved)
            except Exception as e:
                logger.warning(f"Verification error: {e}")
                passed = False
                msg = str(e)

            try:
                record_usage(rule_id, passed)
            except Exception as e:
                logger.warning(f"Telemetry error (non-blocking): {e}")

            if passed:
                if args.dry_run:
                    print("─── DRY-RUN OUTPUT ───")
                    print(patched)
                    print("─────────────────────")
                else:
                    if output_path.exists() and not args.force:
                        logger.error(f"File output '{output_path}' sudah ada. Gunakan --force untuk menimpa.")
                        sys.exit(EXIT_IO_ERROR)
                    try:
                        atomic_write(output_path, patched, backup=args.backup)
                    except OSError as e:
                        logger.error(str(e))
                        sys.exit(EXIT_IO_ERROR)
                    logger.info(f"Kode berhasil diperbaiki! Output: {output_path}")
                logger.info(msg)
                applied = True
                return True
            else:
                logger.warning(f"Verifikasi gagal: {msg}")
                return False

        for rule in matched:
            if try_rule(rule):
                break
            fallbacks = rule.get("fallbacks", [])
            for fb in fallbacks:
                fb_id = fb.get("id") if isinstance(fb, dict) else fb
                if not fb_id:
                    continue
                fb_rule = loader.get_by_id(fb_id)
                if fb_rule and try_rule(fb_rule):
                    break
            if applied:
                break

        if not applied:
            logger.error("Tidak ada rule yang berhasil memperbaiki kode.")
            sys.exit(EXIT_ERROR)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Dibatalkan oleh pengguna")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Kesalahan tak terduga: {e}")
        sys.exit(EXIT_ERROR)
