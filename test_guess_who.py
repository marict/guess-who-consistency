import json
import unittest
from unittest.mock import patch

import guess_who as gw


class ExperimentTests(unittest.TestCase):
    def test_full_tree_size(self):
        paths = gw.paths_for("full", 25, 42)
        self.assertEqual(len(paths), 3125)
        self.assertEqual(len(gw.prefixes_for(paths)) + 1, 3906)

    def test_samples_reproducible_unique(self):
        paths = gw.paths_for("sample", 25, 42)
        self.assertEqual(paths, gw.paths_for("sample", 25, 42))
        self.assertEqual(len(set(paths)), 25)

    def test_shared_prefix_once_and_siblings_isolated(self):
        paths = [(0, 0, 0, 0, 0), (0, 0, 0, 0, 1)]
        records = []

        def client(model, messages):
            question = messages[-1]["content"]
            content = "Yes."
            if question.startswith("Question 5"):
                content = json.dumps({"answer": "No", "identity": "Ada Lovelace" if "magic" in question else "Albert Einstein"})
            return {"choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                    "usage": {"total_tokens": 10}}

        summary = gw.run_model("fake", paths, client, records.append)
        self.assertEqual(len(records), 7)
        self.assertEqual(records[-1]["messages"][:-1], records[-2]["messages"][:-1])
        self.assertEqual(len(records[-1]["messages"]), 12)
        self.assertEqual(records[0]["messages"][-1]["content"], gw.OPENING)
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["distinct_names"], 2)
        self.assertEqual(summary["pairwise_agreement"], 0)
        self.assertEqual(summary["usage_reported"]["total_tokens"], 70)

    def test_failed_root_skips_descendants(self):
        def fail(*args):
            raise RuntimeError("unavailable")
        summary = gw.run_model("fake", [(0, 0, 0, 0, 0)], fail, lambda r: None)
        self.assertEqual(summary["attempted_calls"], 1)
        self.assertEqual(summary["completed_leaves"], 0)
        self.assertFalse(summary["all_endings_agree"])

    def test_truncated_reveal_excluded(self):
        def client(model, messages):
            final = messages[-1]["content"].startswith("Question 5")
            return {"choices": [{"message": {"content": '{"identity":"Ada Lovelace"}'},
                                 "finish_reason": "length" if final else "stop"}]}
        summary = gw.run_model("fake", [(0, 0, 0, 0, 0)], client, lambda r: None)
        self.assertFalse(summary["complete"])
        self.assertEqual(summary["valid_reveals"], 0)

    def test_invalid_json_not_counted_as_identity(self):
        for content in ('I chose Ada.', '[]', '{"identity": null}', '{"identity":" "}'):
            self.assertIsNone(gw.parse_identity(content))
        self.assertEqual(gw.parse_identity('```json\n{"identity":"Ada"}\n```'), "Ada")

    def test_budget_rejects_before_network(self):
        with patch.object(gw.Fal, "__call__") as call:
            with self.assertRaises(SystemExit):
                gw.main(["--model", "fake", "--run", "--max-calls", "1"])
            call.assert_not_called()

    def test_pairwise_and_normalization(self):
        result = gw.agreement(["Ada Lovelace", " ada  LOVELACE ", "Einstein"])
        self.assertAlmostEqual(result["pairwise_agreement"], 1 / 3)
        self.assertAlmostEqual(result["majority_fraction"], 2 / 3)


if __name__ == "__main__":
    unittest.main()
