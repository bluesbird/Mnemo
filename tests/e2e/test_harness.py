"""Fast checks of the deterministic fake and polling, without Docker."""

import json
import http.client
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from fake_ollama import Handler, respond
from run import verify_ms1_json_logs
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

    def test_manual_summary_has_a_complete_response(self):
        response = respond("/api/chat", {
            "model": "test",
            "stream": False,
            "messages": [{"content": "Create a short summary of this note.\nTitle: Test\nContent: Details"}],
        })
        self.assertEqual(response["done_reason"], "stop")
        self.assertEqual(response["message"]["content"], "This note records access details.")

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
            self.assertEqual(json.loads(response.read())["done_reason"], "stop")
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

    def test_ms1_structured_log_fields(self):
        verify_ms1_json_logs(json.dumps(self.ms1_startup_record()))

    def test_ms1_plain_text_logs_fail_verification(self):
        with self.assertRaisesRegex(AssertionError, "Missing MS1 structured startup log"):
            verify_ms1_json_logs("INFO Started KnowledgeServiceApplication")

    def test_ms1_missing_log_fields_fail_verification(self):
        for field in self.ms1_startup_record():
            with self.subTest(field=field):
                record = self.ms1_startup_record()
                del record[field]
                with self.assertRaises(AssertionError):
                    verify_ms1_json_logs(json.dumps(record))

    def test_ms1_wrong_service_fails_verification(self):
        record = self.ms1_startup_record()
        record["service"]["name"] = "another-service"
        with self.assertRaises(AssertionError):
            verify_ms1_json_logs(json.dumps(record))

    def test_ms1_missing_nested_fields_fail_verification(self):
        for parent, field in (("log", "level"), ("log", "logger"), ("service", "name")):
            with self.subTest(parent=parent, field=field):
                record = self.ms1_startup_record()
                del record[parent][field]
                with self.assertRaises(AssertionError):
                    verify_ms1_json_logs(json.dumps(record))

    def test_ms1_malformed_json_fails_verification(self):
        with self.assertRaisesRegex(AssertionError, "Invalid MS1 JSON log"):
            verify_ms1_json_logs("{invalid")

    @staticmethod
    def ms1_startup_record():
        return {
            "@timestamp": "2026-10-17T00:00:00Z",
            "log": {
                "level": "INFO",
                "logger": "com.mnemo.knowledgeservice.KnowledgeServiceApplication",
            },
            "message": "Started KnowledgeServiceApplication in 5 seconds",
            "service": {"name": "ms1-knowledge-service"},
        }


if __name__ == "__main__":
    unittest.main()
