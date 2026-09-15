from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Protocol


SUPPORTED_LOCALES = {"ru", "kk"}


class IntentClassifier(Protocol):
    def classify(
        self,
        message: str,
        locale: str,
        services: list[dict[str, Any]],
    ) -> tuple[str | None, float] | None: ...


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[\wәіңғүұқөһё]+", value.lower()))


class ServiceAgent:
    def __init__(
        self,
        catalog_path: Path,
        classifier: IntentClassifier | None = None,
    ) -> None:
        with catalog_path.open(encoding="utf-8") as catalog_file:
            self.catalog = json.load(catalog_file)
        self.classifier = classifier

    @property
    def ai_enabled(self) -> bool:
        return self.classifier is not None

    def route(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = str(payload.get("message", "")).strip()
        locale = str(payload.get("locale", "ru"))
        answers = payload.get("answers") or {}

        if locale not in SUPPORTED_LOCALES:
            locale = "ru"
        if not message:
            return {
                "status": "error",
                "message": self._text(locale, "Опишите вашу ситуацию.", "Жағдайыңызды сипаттаңыз."),
            }

        service, confidence = self._match(message, locale)
        if service is None:
            return self._unsupported(locale)

        if service["contentStatus"] != "verified":
            return {
                "status": "content_unavailable",
                "matchedServiceId": service["id"],
                "serviceTitle": service["title"][locale],
                "message": self._text(
                    locale,
                    "Ситуация распознана, но сведения по этой услуге ещё не проверены по официальному источнику.",
                    "Жағдай анықталды, бірақ бұл қызмет туралы мәлімет ресми дереккөз бойынша әлі тексерілмеген.",
                ),
            }

        for clarification in service["clarifications"]:
            if clarification["id"] not in answers:
                return {
                    "status": "needs_clarification",
                    "question": {
                        "id": clarification["id"],
                        "text": clarification["text"][locale],
                        "options": clarification["options"][locale],
                    },
                    "matchedServiceId": service["id"],
                    "confidence": confidence,
                }

        return {
            "status": "ready",
            "catalogVersion": self.catalog["catalogVersion"],
            "service": {
                "id": service["id"],
                "title": service["title"][locale],
                "reason": self._text(
                    locale,
                    "Ваш запрос связан с переездом и регистрацией по новому адресу.",
                    "Сіздің сұрауыңыз көшуге және жаңа мекенжай бойынша тіркелуге қатысты.",
                ),
            },
            "answers": answers,
            "documents": [item[locale] for item in service["documents"]],
            "steps": [item[locale] for item in service["steps"]],
            "channels": service["channels"],
            "source": service["source"],
            "notice": self._text(
                locale,
                "Справочная информация. Перед подачей заявления проверьте требования на официальном ресурсе.",
                "Анықтамалық ақпарат. Өтініш берер алдында талаптарды ресми ресурстан тексеріңіз.",
            ),
        }

    def _match(self, message: str, locale: str) -> tuple[dict[str, Any] | None, float]:
        if self.classifier is not None:
            classified = self.classifier.classify(
                message,
                locale,
                self.catalog["services"],
            )
            if classified is not None:
                service_id, confidence = classified
                service = next(
                    (
                        candidate
                        for candidate in self.catalog["services"]
                        if candidate["id"] == service_id
                    ),
                    None,
                )
                return service, round(confidence, 2)

        return self._match_locally(message, locale)

    def _match_locally(self, message: str, locale: str) -> tuple[dict[str, Any] | None, float]:
        normalized = _normalize(message)
        best_service = None
        best_score = 0

        for service in self.catalog["services"]:
            score = sum(
                1 for keyword in service["keywords"][locale]
                if _normalize(keyword) in normalized
            )
            if score > best_score:
                best_service = service
                best_score = score

        if best_service is None:
            return None, 0.0

        confidence = min(0.55 + (best_score * 0.16), 0.95)
        return best_service, round(confidence, 2)

    def _unsupported(self, locale: str) -> dict[str, Any]:
        return {
            "status": "unsupported",
            "message": self._text(
                locale,
                "Пока я умею помогать только с пятью ситуациями из демонстрационного каталога.",
                "Әзірге мен демонстрациялық каталогтағы бес жағдай бойынша ғана көмектесе аламын.",
            ),
            "supportedServices": [service["title"][locale] for service in self.catalog["services"]],
        }

    @staticmethod
    def _text(locale: str, ru: str, kk: str) -> str:
        return kk if locale == "kk" else ru
