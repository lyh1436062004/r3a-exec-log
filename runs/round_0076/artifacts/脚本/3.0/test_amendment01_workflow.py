"""Zero-API regression checks for amendment-only orchestration and reporting."""
import importlib
import json
import tempfile
import unittest
from pathlib import Path

analysis = importlib.import_module("23_analyze")
workflow = importlib.import_module("26_run_amendment01")


class AmendmentOuterWorkflowTests(unittest.TestCase):
    def test_gate_outcome_diagnostic_keeps_replay_drift_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            context = root / "contexts" / "memos" / "A2.jsonl"
            context.parent.mkdir(parents=True)
            rows = [{"case_id": "0", "cache_key": "k0", "no_op": True},
                    {"case_id": "1", "cache_key": "k1", "no_op": False},
                    {"case_id": "2", "cache_key": "k2", "no_op": True, "bypass": True},
                    {"case_id": "0", "cache_key": "stale", "no_op": False}]
            context.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            verdicts = {"B0": {"0": {"label": "correct"}, "1": {"label": "hallucination"}, "2": {"label": "correct"}},
                        "A2": {"0": {"label": "hallucination"}, "1": {"label": "correct"}, "2": {"label": "omission"}}}
            result = analysis.gate_outcome_diagnostic(root, {"0", "1", "2"}, verdicts,
                                                       {"context_keys": {"A2": {"0": "k0", "1": "k1", "2": "k2"}}})
            groups = {row["branch"]: row for row in result}
            self.assertEqual(groups["gated_noop"]["C_to_H"], 1)
            self.assertEqual(groups["safe_bypass"]["C_to_O"], 1)
            self.assertEqual(groups["intervened"]["wrong_to_C"], 1)
            self.assertEqual(sum(row["n_paired"] for row in result), 3)

    def test_stage_e_flip_uses_archived_wrong_not_absent_fresh_b0(self):
        samples = {str(i): {"evaluation_scope": "archived_wrong_only_stage_E_flip_rate_only",
                            "baseline_label": "hallucination"} for i in range(3)}
        verdicts = {"B1": {"0": {"label": "correct"}, "1": {"label": "omission"}, "2": {"label": "correct"}},
                    "A2": {"0": {"label": "correct"}, "1": {"label": "hallucination"}}}
        result = analysis.rates_and_pairs(samples, verdicts)
        rows = {row["arm"]: row for row in result["flips"]}
        self.assertEqual(rows["B1"]["rescued"], 2)
        self.assertEqual(rows["B1"]["n_paired"], 3)
        self.assertEqual(rows["B1"]["flip_rate"], 2 / 3)
        self.assertEqual(rows["A2"]["n_paired"], 2)
        self.assertEqual(rows["A2"]["missing"], 1)
        self.assertEqual(rows["A2"]["flip_rate"], .5)
        self.assertTrue(all(row["baseline_correct_paired"] == 0 for row in result["harm"]))
        self.assertTrue(all(row["C_to_H"] is None for row in result["harm"]))

    def test_stage_e_unknown_baseline_is_rejected(self):
        with self.assertRaises(ValueError):
            analysis.rates_and_pairs({"x": {"evaluation_scope": "archived_wrong_only", "baseline_label": "correct"}}, {})

    def test_each_paid_phase_preserves_budget_and_alpha(self):
        counts = {"memos": 4062, "mem0": 4476, "memobase": 4940, "supermemory": 184, "longmemeval": 500}
        stages = workflow.workflow()
        self.assertEqual(len({name for name, _ in stages}), len(stages))
        for name, args in stages:
            if args[0] == "23_analyze.py":
                self.assertNotIn("--lambda-o", args)
                self.assertNotIn("--tau", args)
            if args[0] != "21_run_generation.py":
                continue
            self.assertEqual(args[args.index("--alpha") + 1], "0.20")
            pool = args[args.index("--pool") + 1]
            n = int(args[args.index("--subset") + 1]) if "--subset" in args else counts[pool]
            arms = len(args[args.index("--arm") + 1].split(","))
            self.assertLessEqual(n + n * arms * (3 if pool == "longmemeval" else 2), 30000, name)
            if pool == "longmemeval":
                self.assertEqual(args[args.index("--tau") + 1], "0.15")

    def test_frozen_core_pool_and_no_leakage(self):
        workflow.verify_frozen()


if __name__ == "__main__":
    unittest.main()
