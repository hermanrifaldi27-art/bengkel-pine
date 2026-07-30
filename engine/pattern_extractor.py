#!/usr/bin/env python3
"""
Pattern Extractor v1.0 — Belajar dari kode yang diekstrak, simpan pola baru ke knowledge base.
"""
import os, yaml, hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from engine.unified_auditor import UnifiedFinding, UnifiedReport

@dataclass
class LearnedPattern:
    """Pola yang dipelajari dari kode yang diekstrak."""
    id: str                          # hash-based ID
    category: str                    # reliability, memory, performance, dll.
    name: str                        # nama deskriptif
    description: str                 # deskripsi pola
    severity: str                    # ERROR, WARNING, INFO, HINT
    evidence_count: int = 0          # berapa kali ditemukan
    source_files: List[str] = field(default_factory=list)  # file mana saja
    confidence: float = 0.0          # 0.0 - 1.0
    auto_generated: bool = True      # flag: ini hasil pembelajaran

class PatternExtractor:
    """Ekstrak pola baru dari hasil unified audit."""

    def __init__(self, knowledge_path: str = "knowledge/bases/patterns"):
        self.knowledge_path = knowledge_path
        os.makedirs(knowledge_path, exist_ok=True)

    def extract_patterns(self, report: UnifiedReport) -> List[LearnedPattern]:
        """Ekstrak pola yang belum ada di plugin rules dari laporan terpadu."""
        patterns = []

        # 1. Deteksi pola berulang dari Extractor
        extractor_findings = [f for f in report.findings if f.source == 'extractor']
        if len(extractor_findings) >= 3:
            # Banyak masalah = pola kompleksitas
            pattern = self._create_pattern(
                category='complexity',
                name='high_issue_density',
                description=f'File ini memiliki {len(extractor_findings)} masalah — pertimbangkan refactoring',
                severity='WARNING',
                evidence_count=len(extractor_findings),
                source_file=report.file_path
            )
            patterns.append(pattern)

        # 2. Deteksi best practice yang konsisten
        plugin_findings = [f for f in report.findings if f.source == 'plugin' and f.points > 0]
        if len(plugin_findings) >= 5:
            pattern = self._create_pattern(
                category='quality',
                name='high_best_practice_count',
                description=f'File ini memiliki {len(plugin_findings)} best practice — kode berkualitas tinggi',
                severity='INFO',
                evidence_count=len(plugin_findings),
                source_file=report.file_path
            )
            patterns.append(pattern)

        # 3. Deteksi kombinasi spesifik (misal: banyak objek + banyak drawing = visual kompleks)
        obj_count = sum(1 for f in report.findings if 'obj' in f.category.lower())
        drawing_count = sum(1 for f in report.findings if 'drawing' in f.detector_id.lower())
        if obj_count >= 2 and drawing_count >= 2:
            pattern = self._create_pattern(
                category='render',
                name='visual_complexity',
                description=f'Terdeteksi {obj_count} objek + {drawing_count} drawing — visual mungkin terlalu ramai',
                severity='INFO',
                evidence_count=obj_count + drawing_count,
                source_file=report.file_path
            )
            patterns.append(pattern)

        # 4. Deteksi file dengan skor rendah = prioritas perbaikan
        if report.total_score < 70:
            pattern = self._create_pattern(
                category='priority',
                name='low_score_alert',
                description=f'Skor {report.total_score}/100 — file ini perlu perbaikan prioritas tinggi',
                severity='WARNING',
                evidence_count=1,
                source_file=report.file_path
            )
            patterns.append(pattern)

        # Simpan pola yang ditemukan
        for pattern in patterns:
            self._save_pattern(pattern)

        return patterns

    def _create_pattern(self, category: str, name: str, description: str, 
                        severity: str, evidence_count: int, source_file: str) -> LearnedPattern:
        """Buat pola dengan ID berbasis hash."""
        hash_input = f"{category}:{name}:{description}"
        pattern_id = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        
        return LearnedPattern(
            id=pattern_id,
            category=category,
            name=name,
            description=description,
            severity=severity,
            evidence_count=evidence_count,
            source_files=[source_file],
            confidence=min(1.0, evidence_count / 10.0)  # 10 bukti = confidence 100%
        )

    def _save_pattern(self, pattern: LearnedPattern):
        """Simpan pola ke file YAML di knowledge base."""
        yaml_path = os.path.join(self.knowledge_path, f"pattern_{pattern.id}.yaml")
        
        data = {
            'id': pattern.id,
            'category': pattern.category,
            'name': pattern.name,
            'description': pattern.description,
            'severity': pattern.severity,
            'evidence_count': pattern.evidence_count,
            'source_files': pattern.source_files,
            'confidence': pattern.confidence,
            'auto_generated': pattern.auto_generated,
        }
        
        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    
    def get_learned_patterns(self, min_confidence: float = 0.3) -> List[dict]:
        """Ambil semua pola yang sudah dipelajari dengan confidence minimum."""
        patterns = []
        if not os.path.exists(self.knowledge_path):
            return patterns
        
        for fname in os.listdir(self.knowledge_path):
            if fname.endswith('.yaml'):
                fpath = os.path.join(self.knowledge_path, fname)
                try:
                    with open(fpath, 'r') as f:
                        data = yaml.safe_load(f)
                    if data and data.get('confidence', 0) >= min_confidence:
                        patterns.append(data)
                except Exception:
                    pass
        
        return sorted(patterns, key=lambda p: p.get('confidence', 0), reverse=True)

    def summary(self) -> str:
        """Ringkasan knowledge base pola."""
        patterns = self.get_learned_patterns()
        return f"{len(patterns)} pola dipelajari dari kode yang diekstrak"
