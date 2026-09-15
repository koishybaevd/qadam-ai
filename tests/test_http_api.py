import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

import app


class HttpApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_classifier = app.AGENT.classifier
        app.AGENT.classifier = None
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.QadamHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        app.AGENT.classifier = cls.original_classifier

    def test_health_reports_local_fallback(self):
        with urllib.request.urlopen(f"{self.base_url}/api/health") as response:
            payload = json.load(response)
        self.assertEqual(payload, {"status": "ok", "routingMode": "local_fallback"})

    def test_route_endpoint_returns_first_clarification(self):
        body = json.dumps(
            {
                "message": "Я переехал и хочу зарегистрироваться по новому адресу",
                "locale": "ru",
                "answers": {},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/route",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            payload = json.load(response)
        self.assertEqual(payload["status"], "needs_clarification")
        self.assertEqual(payload["question"]["id"], "registration_type")


if __name__ == "__main__":
    unittest.main()

