import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "脚本" / "3.0"


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


run = load_module("exp7_run", "14_run_containment_audit.py")
analyze = load_module("exp7_analyze", "15_analyze_containment_audit.py")


class Experiment7ContainmentAuditTests(unittest.TestCase):
    def test_deterministic_label_mapping(self):
        self.assertEqual(run.derive_audit_label("missing", "missing", True), "A_evidence_missing")
        self.assertEqual(run.derive_audit_label("partial", "partial", True), "A_evidence_missing")
        self.assertEqual(run.derive_audit_label("contained", "partial", True), "B_present_not_rendered")
        self.assertEqual(run.derive_audit_label("contained", "contained", True), "C_rendered_not_used")
        self.assertEqual(run.derive_audit_label("contained", "contained", False), "D_judge_error")

    def test_response_validation_flags_impossible_rendering_gain(self):
        result = run.validate_audit_response(
            {
                "raw_coverage": "missing",
                "rendered_coverage": "contained",
                "direct_gold_recovery_valid": True,
                "raw_supporting_memory_indices": [],
                "raw_supporting_fields": [],
                "missing_material_facts": ["x"],
                "facts_lost_in_rendering": [],
                "temporal_information_status": "ambiguous",
                "consistency_error": False,
                "rationale": "test",
            }
        )
        self.assertTrue(result["consistency_error"])
        self.assertEqual(result["audit_label"], "A_evidence_missing")

    def test_frozen_workbook_recomputes_exact_158_pool(self):
        rows, provenance = run.load_frozen_source_rows(run.SOURCE_WORKBOOK)
        self.assertEqual(len(rows), 158)
        self.assertEqual(provenance["recomputed_class_counts"], run.EXPECTED_SOURCE_COUNTS)
        self.assertEqual(provenance["stale_recommended_class_disagreements"], 18)
        self.assertEqual(provenance["final_class_disagreements"], 0)
        self.assertEqual(provenance["source_workbook_sha256"], run.EXPECTED_WORKBOOK_SHA256)

    def test_candidate_pool_excludes_retrieval_label_features(self):
        candidates, _ = run.build_candidate_pool(run.SOURCE_WORKBOOK)
        self.assertEqual(len(candidates), 158)
        forbidden = {
            "gold_memory_ids",
            "partial_memory_ids",
            "other_memory_ids",
            "support_evidence_results",
        }
        self.assertTrue(all(not (forbidden & set(candidate)) for candidate in candidates))

    def test_human_sample_is_deterministic_and_stratified(self):
        rows = []
        for index in range(40):
            rows.append(
                {
                    "case_id": f"a:{index}",
                    "raw_coverage": "missing",
                    "audit_label": "A_evidence_missing",
                    "consistency_error": False,
                }
            )
        for index in range(40):
            rows.append(
                {
                    "case_id": f"c:{index}",
                    "raw_coverage": "contained",
                    "audit_label": "C_rendered_not_used",
                    "consistency_error": False,
                }
            )
        first = analyze.deterministic_human_sample(rows)
        second = analyze.deterministic_human_sample(rows)
        self.assertEqual([row["case_id"] for row in first], [row["case_id"] for row in second])
        self.assertEqual(len(first), 60)
        self.assertEqual(
            sum(row["validation_stratum"] == "raw_partial_or_missing" for row in first), 30
        )
        self.assertEqual(sum(row["validation_stratum"] == "raw_contained" for row in first), 30)


if __name__ == "__main__":
    unittest.main()
