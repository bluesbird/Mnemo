"""Fast checks of the deterministic fake and polling, without Docker."""

import unittest
from unittest.mock import patch

from fake_ollama import respond
from scenario import eventually


class HarnessTests(unittest.TestCase):
    def test_embeddings_are_deterministic_and_batch_aligned(self):
        payload = {"input": ["one", "two"]}
        self.assertEqual(respond("/api/embed", payload),
                         {"embeddings": [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]})
        self.assertEqual(respond("/api/embed", payload), respond("/api/embed", payload))

    def test_chat_echoes_context_not_question(self):
        response = respond("/api/chat", {
            "stream": False,
            "messages": [{"content": "NOTES:\nold indexed fact\n\nQUESTION: new unindexed fact"}],
        })
        self.assertEqual(response["message"]["content"], "old indexed fact")

    def test_unsupported_endpoint_fails(self):
        with self.assertRaises(ValueError):
            respond("/unexpected", {})

    def test_poll_retries_assertion_until_success(self):
        with patch("scenario.time.sleep") as sleep:
            probe = unittest.mock.Mock(side_effect=[AssertionError("not yet"), True])
            self.assertTrue(eventually("test", probe))
            self.assertEqual(probe.call_count, 2)
            sleep.assert_called_once()

    def test_timeout_includes_last_observation(self):
        with self.assertRaisesRegex(AssertionError, "last observation:.*missing source"):
            eventually("test", unittest.mock.Mock(side_effect=AssertionError("missing source")),
                       timeout=0)


if __name__ == "__main__":
    unittest.main()
