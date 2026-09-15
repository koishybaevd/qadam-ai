import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qadam.agent import ServiceAgent


class ServiceAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = ServiceAgent(ROOT / "data" / "services.json")

    def test_primary_scenario_asks_clarifications_then_returns_route(self):
        message = "Я переехал в Астану и хочу зарегистрироваться по новому адресу"

        first = self.agent.route({"message": message, "locale": "ru", "answers": {}})
        self.assertEqual(first["status"], "needs_clarification")
        self.assertEqual(first["question"]["id"], "registration_type")

        second = self.agent.route({
            "message": message,
            "locale": "ru",
            "answers": {"registration_type": "Постоянная"},
        })
        self.assertEqual(second["status"], "needs_clarification")
        self.assertEqual(second["question"]["id"], "owner_consent")

        final = self.agent.route({
            "message": message,
            "locale": "ru",
            "answers": {
                "registration_type": "Постоянная",
                "owner_consent": "Да",
            },
        })
        self.assertEqual(final["status"], "ready")
        self.assertEqual(final["service"]["id"], "residence-registration")
        self.assertTrue(final["documents"])
        self.assertTrue(final["steps"])
        self.assertTrue(final["source"]["url"].startswith("https://egov.kz/"))

    def test_unverified_service_is_not_presented_as_factual_route(self):
        result = self.agent.route({"message": "Я хочу открыть ИП", "locale": "ru"})
        self.assertEqual(result["status"], "content_unavailable")

    def test_unknown_intent_returns_supported_services(self):
        result = self.agent.route({"message": "Как заказать пиццу?", "locale": "ru"})
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(len(result["supportedServices"]), 5)

    def test_kazakh_locale_is_supported(self):
        result = self.agent.route({"message": "Мен жаңа мекенжайға көшіп келдім", "locale": "kk"})
        self.assertEqual(result["status"], "needs_clarification")
        self.assertIn("тіркеу", result["question"]["text"].lower())

    def test_external_classifier_can_match_a_paraphrased_intent(self):
        class FakeClassifier:
            def classify(self, _message, _locale, _services):
                return "individual-entrepreneur-registration", 0.91

        agent = ServiceAgent(
            ROOT / "data" / "services.json",
            classifier=FakeClassifier(),
        )
        result = agent.route({
            "message": "Хочу легально работать на себя",
            "locale": "ru",
        })
        self.assertEqual(result["status"], "content_unavailable")
        self.assertEqual(result["matchedServiceId"], "individual-entrepreneur-registration")

    def test_classifier_failure_falls_back_to_local_matching(self):
        class FailingClassifier:
            def classify(self, _message, _locale, _services):
                return None

        agent = ServiceAgent(
            ROOT / "data" / "services.json",
            classifier=FailingClassifier(),
        )
        result = agent.route({
            "message": "Я переехал и хочу сделать регистрацию",
            "locale": "ru",
        })
        self.assertEqual(result["status"], "needs_clarification")



if __name__ == "__main__":
    unittest.main()
