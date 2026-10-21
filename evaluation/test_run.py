import json
from collections import Counter
import unittest
from unittest.mock import patch

import run


class EvaluationTests(unittest.TestCase):
    def test_frozen_corpus_and_key(self):
        fixture = json.loads((run.HERE / "fixture.json").read_text(encoding="utf-8"))
        notes = fixture["notes"]
        keys = {note["key"] for note in notes}
        self.assertEqual(len(keys), 10)
        self.assertEqual(Counter(n["length"] for n in notes),
                         {"short": 4, "medium": 3, "long": 3})
        questions = fixture["questions"]
        self.assertEqual([q["id"] for q in questions], [f"Q{i}" for i in range(1, 11)])
        self.assertEqual(sum(bool(q.get("expected_abstention")) for q in questions), 3)
        for question in questions:
            self.assertTrue(set(question["required_sources"]) <= keys)
            self.assertEqual(bool(question["required_facts"]),
                             not question.get("expected_abstention", False))
            self.assertEqual(bool(question["required_sources"]),
                             not question.get("expected_abstention", False))

    def test_refuses_to_overwrite_first_run(self):
        with patch.object(run, "OUTPUT") as output, patch.object(run, "command") as command:
            output.exists.return_value = True
            with self.assertRaisesRegex(SystemExit, "preserve the first run"):
                run.main()
            command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
