"""Fast checks of the deterministic fake and polling, without Docker."""

import json
import http.client
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from fake_ollama import Handler, respond
from run import verify_knowledge_json_logs
from scenario import eventually


class HarnessTests(unittest.TestCase):
    def test_embeddings_are_deterministic_and_batch_aligned(self):
        payload = {"input": ["one", "two"]}
        self.assertEqual(respond("/api/embed", payload),
                         {"embeddings": [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]})

    def test_chat_echoes_context_not_question(self):
        response = respond("/api/chat", {
            "stream": False,
            "messages": [{"content": "NOTES:\nold indexed fact\n\nQUESTION: new unindexed fact"}],
        })
        self.assertEqual(response["message"]["content"], "old indexed fact")

    def test_unsupported_endpoint_fails(self):
        with self.assertRaises(ValueError):
            respond("/unexpected", {})

    def test_summary_fake_accepts_chunked_requests_from_spring(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection(*server.server_address, timeout=5)
        try:
            payload = json.dumps({
                "model": "test",
                "stream": False,
                "messages": [{"content": "Create a short summary of this note.\nTitle: Test"}],
            }).encode()
            connection.request("POST", "/api/chat", iter([payload[:20], payload[20:]]),
                               {"Content-Type": "application/json"}, encode_chunked=True)
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            result = json.loads(response.read())
            self.assertEqual(result["done_reason"], "stop")
            self.assertEqual(result["message"]["content"], "This note records access details.")
            self.assertGreater(result["prompt_eval_count"], 0)
            self.assertGreater(result["eval_count"], 0)
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join()

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

    def test_knowledge_structured_log_fields(self):
        verify_knowledge_json_logs(json.dumps(self.knowledge_startup_record()))

    def test_knowledge_plain_text_logs_fail_verification(self):
        with self.assertRaisesRegex(AssertionError, "Missing Knowledge service structured startup log"):
            verify_knowledge_json_logs("INFO Started KnowledgeServiceApplication")

    def test_knowledge_incomplete_or_wrong_service_logs_fail_verification(self):
        for change in ({"message": ""}, {"log": {}}, {"service": {"name": "another-service"}}):
            with self.subTest(change=change), self.assertRaises(AssertionError):
                verify_knowledge_json_logs(json.dumps(self.knowledge_startup_record() | change))

    def test_knowledge_malformed_json_fails_verification(self):
        with self.assertRaisesRegex(AssertionError, "Invalid Knowledge service JSON log"):
            verify_knowledge_json_logs("{invalid")

    @staticmethod
    def knowledge_startup_record():
        return {
            "@timestamp": "2026-10-17T00:00:00Z",
            "log": {
                "level": "INFO",
                "logger": "com.mnemo.knowledgeservice.KnowledgeServiceApplication",
            },
            "message": "Started KnowledgeServiceApplication in 5 seconds",
            "service": {"name": "knowledge-service"},
        }


if __name__ == "__main__":
    unittest.main()
