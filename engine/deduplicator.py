#!/usr/bin/env python3
"""Deduplicator — Pastikan knowledge base bebas duplikasi & berkualitas."""
import os, yaml, hashlib
from pathlib import Path

class Deduplicator:
    BASE_PATH = Path("knowledge/bases/fixes")

    @classmethod
    def check_all(cls) -> dict:
        """Periksa semua file YAML, deteksi duplikasi, beri laporan."""
        result = {'total_files': 0, 'total_rules': 0, 'duplicates': [], 'unique': []}
        seen = {}
        
        if not cls.BASE_PATH.exists():
            return result
        
        for yf in sorted(cls.BASE_PATH.glob("*.yaml")):
            result['total_files'] += 1
            try:
                with open(yf, 'r') as f:
                    data = yaml.safe_load(f) or {}
                rules = data.get('rules', [])
                for rule in rules:
                    result['total_rules'] += 1
                    rid = rule.get('id', '')
                    sig = rule.get('signature', '')
                    key = rid or sig or hashlib.md5(str(rule).encode()).hexdigest()[:8]
                    if key in seen:
                        result['duplicates'].append({
                            'key': key,
                            'file1': seen[key],
                            'file2': str(yf)
                        })
                    else:
                        seen[key] = str(yf)
                        result['unique'].append(key)
            except Exception as e:
                print(f"⚠️  Gagal baca {yf}: {e}")
        
        return result

    @classmethod
    def deduplicate(cls, dry_run: bool = True) -> int:
        """Hapus file YAML duplikat. Return jumlah yang dihapus."""
        report = cls.check_all()
        removed = 0
        for dup in report['duplicates']:
            file_to_remove = dup['file2']
            if dry_run:
                print(f"  [DRY-RUN] Akan hapus duplikat: {file_to_remove}")
            else:
                try:
                    os.remove(file_to_remove)
                    print(f"  ✅ Dihapus: {file_to_remove}")
                    removed += 1
                except Exception as e:
                    print(f"  ❌ Gagal hapus {file_to_remove}: {e}")
        return removed

    @classmethod
    def format_report(cls, report: dict) -> str:
        out = []
        out.append(f"Knowledge Base: {report['total_files']} file, {report['total_rules']} rules")
        out.append(f"Unique: {len(report['unique'])} | Duplikat: {len(report['duplicates'])}")
        if report['duplicates']:
            out.append("\nDuplikat ditemukan:")
            for d in report['duplicates']:
                out.append(f"  - {d['key']}: {d['file1']} = {d['file2']}")
        else:
            out.append("✅ Tidak ada duplikasi.")
        return '\n'.join(out)
