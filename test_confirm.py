import copy
import json
from pathlib import Path
import tempfile
import unittest

import confirm


def completion(content, finish="stop"):
    return {"choices": [{"message": {"content": content}, "finish_reason": finish}]}


class ConfirmationTests(unittest.TestCase):
    def ending(self):
        return {"model": "fake", "path": [0]*5,
                "messages": [{"role": "user", "content": "original history"}],
                "response": completion('{"identity":"Ada Lovelace"}')}

    def test_exact_followup_preserves_ending_and_does_not_mutate_source(self):
        ending = self.ending()
        original = copy.deepcopy(ending)
        def client(model, messages):
            self.assertEqual(model, "fake")
            self.assertEqual(messages, original["messages"] + [
                {"role": "assistant", "content": '{"identity":"Ada Lovelace"}'},
                {"role": "user", "content": "confirming did you actually lock in an answer"}])
            return completion("Yes, I did.")
        self.assertEqual(confirm.confirm_ending(ending, client)["classification"], "yes")
        self.assertEqual(ending, original)

    def test_classification_keeps_non_explicit_replies_unclear(self):
        for text, expected in [('Yes, I did.', 'yes'), ('No. I did not.', 'no'),
                               ('**Yes**.', 'yes'), ('Yesterday I chose.', 'unclear'),
                               ('I picked Ada.', 'unclear'), ('Not really.', 'unclear'),
                               ('{"answer":"No, I did not"}', 'no'),
                               ('```json\n{"answer":"Yes"}\n```', 'yes')]:
            self.assertEqual(confirm.classify(text), expected)

    def test_truncated_confirmation_is_error_even_if_it_starts_yes(self):
        result = confirm.confirm_ending(self.ending(), lambda *args: completion("Yes", "length"))
        self.assertEqual(result["classification"], "error")

    def test_incomplete_original_is_preserved_and_flagged(self):
        ending = self.ending()
        ending["response"] = completion('partial ending', 'length')
        ending["error"] = 'truncated'
        result = confirm.confirm_ending(ending, lambda *args: completion('No.'))
        self.assertEqual(result['source_finish_reason'], 'length')
        summary = confirm.summarize([result])[0]
        self.assertEqual(summary['no'], 1)
        self.assertEqual(summary['normal_source_endings'], 0)

    def test_missing_original_text_does_not_call_api(self):
        ending = self.ending()
        ending['response'] = completion(None)
        def client(*args):
            self.fail('Should not call the API')
        self.assertEqual(confirm.confirm_ending(ending, client)['classification'], 'error')

    def test_duplicate_source_rejected_before_paid_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'transcripts.jsonl'
            source.write_text((json.dumps(self.ending())+'\n')*2)
            with self.assertRaises(ValueError):
                confirm.load_endings(source)


if __name__ == '__main__':
    unittest.main()
