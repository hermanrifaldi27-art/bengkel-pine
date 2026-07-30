#!/usr/bin/env python3
"""
Knowledge Base Proaktif v1.0 — Otomatis menyerap temuan Extractor, update confidence, siapkan fix.
"""
import os, yaml, hashlib, re
from typing import List, Dict, Any, Optional
from datetime import datetime

class ProactiveKnowledgeBase:
    """Knowledge Base yang proaktif: setiap temuan Extractor langsung disimpan & di-update."""

    def __init__(self, base_path: str = "knowledge/bases"):
        self.base_path = base_path
        self.fixes_path = os.path.join(base_path, "fixes")
        os.makedirs(self.fixes_path, exist_ok=True)

    def absorb_finding(self, finding: Any) -> bool:
        """
        Serap satu temuan dari Extractor.
        - Jika sudah ada: update evidence_count & confidence
        - Jika belum: simpan sebagai aturan baru
        """
        # Generate ID dari detector_id + anchor
        detector_id = getattr(finding, 'detector_id', 'unknown')
        anchor = getattr(finding, 'anchor', 'unknown')
        raw_id = f"{detector_id}:{anchor}"
        rule_id = hashlib.md5(raw_id.encode()).hexdigest()[:12]

        yaml_path = os.path.join(self.fixes_path, f"fix_{rule_id}.yaml")

        # Cek apakah sudah ada
        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, 'r') as f:
                    existing = yaml.safe_load(f) or {}
                existing['evidence_count'] = existing.get('evidence_count', 0) + 1
                existing['confidence'] = min(1.0, existing['evidence_count'] / 10.0)
                existing['last_seen'] = datetime.now().isoformat()
                existing['module'] = getattr(finding, 'module', 'unknown')
                existing['goal'] = getattr(finding, 'goal', '')
                existing['tactic'] = getattr(finding, 'tactic', '')
                with open(yaml_path, 'w') as f:
                    yaml.dump(existing, f, allow_unicode=True)
                return True
            except Exception:
                return False

        # Simpan baru
        data = {
            'id': rule_id,
            'detector_id': detector_id,
            'module': getattr(finding, 'module', 'unknown'),
            'goal': getattr(finding, 'goal', ''),
            'tactic': getattr(finding, 'tactic', ''),
            'anchor': anchor,
            'severity': self._guess_severity(detector_id),
            'evidence_count': 1,
            'confidence': 0.1,  # 1 bukti = 10% confidence
            'first_seen': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'auto_fix_template': self._generate_fix_template(finding),
        }
        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, allow_unicode=True)
        return True

    def absorb_all(self, features: List[Any]) -> int:
        """Serap semua temuan dari Extractor. Return jumlah yang diserap."""
        count = 0
        for f in features:
            if self.absorb_finding(f):
                count += 1
        return count

    def get_high_confidence_rules(self, min_confidence: float = 0.5) -> List[dict]:
        """Ambil aturan dengan confidence tinggi — siap untuk Auto-Fixer."""
        rules = []
        if not os.path.exists(self.fixes_path):
            return rules
        for fname in os.listdir(self.fixes_path):
            if fname.endswith('.yaml'):
                fpath = os.path.join(self.fixes_path, fname)
                try:
                    with open(fpath, 'r') as f:
                        data = yaml.safe_load(f)
                    if data and data.get('confidence', 0) >= min_confidence:
                        rules.append(data)
                except Exception:
                    pass
        return sorted(rules, key=lambda r: r.get('confidence', 0), reverse=True)

    def get_fix_template(self, detector_id: str) -> Optional[str]:
        """Cari template perbaikan terbaik untuk detector_id."""
        best = None
        best_conf = 0
        for rule in self.get_high_confidence_rules(min_confidence=0.3):
            if rule.get('detector_id') == detector_id and rule.get('confidence', 0) > best_conf:
                best = rule
                best_conf = rule.get('confidence', 0)
        if best:
            return best.get('auto_fix_template')
        return None

    def _guess_severity(self, detector_id: str) -> str:
        """Tebak severity dari detector_id."""
        if any(k in detector_id for k in ['request_security', 'lookahead', 'security_in_loop', 'security_gaps']):
            return 'ERROR'
        if any(k in detector_id for k in ['plot_in_if', 'hline_in_if', 'redundant_plot', 'array_unbounded', 'matrix_unbounded', 'alertcondition', 'drawing_in_loop', 'rebuild']):
            return 'WARNING'
        return 'INFO'

    def _generate_fix_template(self, finding: Any) -> str:
        """Generate template perbaikan dari finding."""
        detector_id = getattr(finding, 'detector_id', '')
        tactic = getattr(finding, 'tactic', '')
        if tactic:
            return tactic
        # Default templates
        templates = {
            'request_security_lookahead_v1': 'request.security(..., lookahead = barmerge.lookahead_off)',
            'security_gaps_v1': 'request.security(..., gaps = barmerge.gaps_off)',
            'var_int_na_v1': 'var int x = 0',
            'obj_in_if_v1': 'var obj = na\nif condition\n    obj := obj.new(...)',
            'drawing_in_loop_v1': 'var obj = na\nif condition\n    obj.set_*(...)',
            'redundant_plot_v1': 'Gunakan series dinamis, bukan literal statis',
        }
        return templates.get(detector_id, '// TODO: Perbaiki sesuai aturan')

    def summary(self) -> str:
        """Ringkasan knowledge base proaktif."""
        fixes = [f for f in os.listdir(self.fixes_path) if f.endswith('.yaml')] if os.path.exists(self.fixes_path) else []
        high_conf = len(self.get_high_confidence_rules(min_confidence=0.5))
        return f"{len(fixes)} fixes ({high_conf} high-confidence)"
