import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qadam.openai_adapter import OpenAIIntentClassifier, _extract_output_text


class OpenAIIntentClassifierTests(unittest.TestCase):
    def test_environment_requires_both_key_and_model(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(OpenAIIntentClassifier.from_environment())

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}, clear=True):
            self.assertIsNone(OpenAIIntentClassifier.from_environment())

        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "test", "OPENAI_MODEL": "test-model"},
            clear=True,
        ):
            self.assertIsInstance(
                OpenAIIntentClassifier.from_environment(),
                OpenAIIntentClassifier,
            )

    def test_extracts_structured_output_text(self):
        expected = {"service_id": "residence-registration", "confidence": 0.9}
        response = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": json.dumps(expected)}
                    ],
                }
            ]
        }
        self.assertEqual(json.loads(_extract_output_text(response)), expected)


if __name__ == "__main__":
    unittest.main()

