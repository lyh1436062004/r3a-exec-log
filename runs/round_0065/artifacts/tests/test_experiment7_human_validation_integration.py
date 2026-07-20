import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "脚本" / "3.0" / "16_integrate_containment_human_validation.py"
spec = importlib.util.spec_from_file_location("exp7_human", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["exp7_human"] = module
spec.loader.exec_module(module)


class Experiment7HumanValidationIntegrationTests(unittest.TestCase):
    def test_human_label_logic(self):
        self.assertIsNone(
            module.validate_human_label_logic(
                {
                    "human_final_label": "A_evidence_missing",
                    "human_raw_coverage": "partial",
                    "human_rendered_coverage": "missing",
                }
            )
        )
        self.assertIsNone(
            module.validate_human_label_logic(
                {
                    "human_final_label": "B_present_not_rendered",
                    "human_raw_coverage": "contained",
                    "human_rendered_coverage": "partial",
                }
            )
        )
        self.assertIsNone(
            module.validate_human_label_logic(
                {
                    "human_final_label": "C_rendered_not_used",
                    "human_raw_coverage": "contained",
                    "human_rendered_coverage": "contained",
                }
            )
        )
        self.assertIsNotNone(
            module.validate_human_label_logic(
                {
                    "human_final_label": "C_rendered_not_used",
                    "human_raw_coverage": "contained",
                    "human_rendered_coverage": "partial",
                }
            )
        )

    def test_projected_estimates_respect_stratum_weights(self):
        rows = []
        for index in range(13):
            rows.append(
                {
                    "validation_stratum": "raw_partial_or_missing",
                    "human_final_label": "A_evidence_missing" if index < 12 else "uncertain",
                }
            )
        for index in range(30):
            label = "B_present_not_rendered" if index < 15 else "C_rendered_not_used"
            rows.append({"validation_stratum": "raw_contained", "human_final_label": label})
        estimates = {row["label"]: row for row in module.projected_label_estimates(rows)}
        self.assertEqual(estimates["A_evidence_missing"]["estimated_count"], 12)
        self.assertEqual(estimates["B_present_not_rendered"]["estimated_count"], 72.5)
        self.assertEqual(estimates["C_rendered_not_used"]["estimated_count"], 72.5)
        self.assertEqual(estimates["uncertain"]["estimated_count"], 1)

    def test_actual_filled_workbook_integrity(self):
        filled = Path(r"C:\Users\78443\Downloads\human_validation_sample_final_confidence_adjusted.xlsx")
        if not filled.exists():
            self.skipTest("user-provided workbook is not available")
        rows, provenance = module.validate_workbook(filled, module.BLANK_WORKBOOK)
        self.assertEqual(len(rows), 43)
        self.assertEqual(provenance["immutable_cell_differences"], 0)
        self.assertEqual(provenance["validation_errors"], 0)

    def test_adjudication_is_explicit_and_non_mutating(self):
        source = [
            {
                "case_id": "memos_long:2093",
                "human_rendered_coverage": "partial",
            }
        ]
        adjusted, trail = module.apply_adjudications(source)
        self.assertEqual(source[0]["human_rendered_coverage"], "partial")
        self.assertEqual(adjusted[0]["human_rendered_coverage"], "contained")
        self.assertEqual(len(trail), 1)
        self.assertEqual(trail[0]["submitted_value"], "partial")


if __name__ == "__main__":
    unittest.main()
