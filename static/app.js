const state = {
  locale: "ru",
  message: "",
  answers: {},
};

const copy = {
  ru: {
    tagline: "Понятный маршрут государственной услуги",
    label: "Опишите ситуацию своими словами",
    privacy: "Не указывайте ИИН, адрес или номер документа",
    submit: "Найти маршрут",
    loading: "Определяю подходящий маршрут…",
    documents: "Что подготовить",
    steps: "Что делать",
    channels: "Где получить",
    source: "Официальный источник",
    retry: "Начать заново",
  },
  kk: {
    tagline: "Мемлекеттік қызметтің түсінікті бағыты",
    label: "Жағдайыңызды өз сөзіңізбен сипаттаңыз",
    privacy: "ЖСН, мекенжай немесе құжат нөмірін көрсетпеңіз",
    submit: "Бағытты табу",
    loading: "Сәйкес бағытты анықтап жатырмын…",
    documents: "Не дайындау керек",
    steps: "Не істеу керек",
    channels: "Қайдан алуға болады",
    source: "Ресми дереккөз",
    retry: "Қайта бастау",
  },
};

const messageInput = document.querySelector("#message");
const result = document.querySelector("#result");
const submitButton = document.querySelector("#submit");

document.querySelectorAll(".locale").forEach((button) => {
  button.addEventListener("click", () => {
    state.locale = button.dataset.locale;
    document.documentElement.lang = state.locale;
    document.querySelectorAll(".locale").forEach((item) => item.classList.toggle("active", item === button));
    applyCopy();
    resetConversation(false);
  });
});

submitButton.addEventListener("click", () => {
  state.message = messageInput.value.trim();
  state.answers = {};
  requestRoute();
});

loadHealth();

async function loadHealth() {
  try {
    const response = await fetch("/api/health", { cache: "no-store" });
    const payload = await response.json();
    document.querySelector("#routing-mode").textContent = payload.routingMode === "openai" ? "OPENAI" : "LOCAL";
  } catch (_error) {
    document.querySelector("#routing-mode").textContent = "OFFLINE";
  }
}

function applyCopy() {
  const text = copy[state.locale];
  document.querySelector("#tagline").textContent = text.tagline;
  document.querySelector("#prompt-label").textContent = text.label;
  document.querySelector("#privacy-note").textContent = text.privacy;
  submitButton.textContent = text.submit;
}

async function requestRoute(answer) {
  if (answer) state.answers[answer.id] = answer.value;
  result.hidden = false;
  result.innerHTML = `<div class="loading">${escapeHtml(copy[state.locale].loading)}</div>`;
  submitButton.disabled = true;

  try {
    const response = await fetch("/api/route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: state.message, locale: state.locale, answers: state.answers }),
    });
    const payload = await response.json();
    render(payload);
  } catch (_error) {
    render({ status: "error", message: "Не удалось связаться с приложением." });
  } finally {
    submitButton.disabled = false;
  }
}

function render(payload) {
  if (payload.status === "needs_clarification") {
    result.innerHTML = `
      <p class="eyebrow">Уточнение</p>
      <h2>${escapeHtml(payload.question.text)}</h2>
      <div class="choices">
        ${payload.question.options.map((option) => `<button data-answer="${escapeHtml(option)}">${escapeHtml(option)}</button>`).join("")}
      </div>`;
    result.querySelectorAll("[data-answer]").forEach((button) => {
      button.addEventListener("click", () => requestRoute({ id: payload.question.id, value: button.dataset.answer }));
    });
    return;
  }

  if (payload.status === "ready") {
    const text = copy[state.locale];
    result.innerHTML = `
      <p class="eyebrow">${escapeHtml(payload.service.id)}</p>
      <h2>${escapeHtml(payload.service.title)}</h2>
      <p class="reason">${escapeHtml(payload.service.reason)}</p>
      ${renderList(text.documents, payload.documents, false)}
      ${renderList(text.steps, payload.steps, true)}
      ${renderList(text.channels, payload.channels, false)}
      <div class="source">
        <span>${escapeHtml(text.source)} · ${escapeHtml(payload.source.verifiedAt)}</span>
        <a href="${escapeHtml(payload.source.url)}" target="_blank" rel="noopener noreferrer">eGov.kz ↗</a>
      </div>
      <p class="notice">${escapeHtml(payload.notice)}</p>
      <button id="reset" class="secondary">${escapeHtml(text.retry)}</button>`;
    document.querySelector("#reset").addEventListener("click", () => resetConversation(true));
    return;
  }

  const services = payload.supportedServices?.length
    ? `<ul>${payload.supportedServices.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : "";
  result.innerHTML = `<h2>${escapeHtml(payload.message || "Ошибка")}</h2>${services}`;
}

function renderList(title, values, ordered) {
  const tag = ordered ? "ol" : "ul";
  return `<section class="route-section"><h3>${escapeHtml(title)}</h3><${tag}>${values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</${tag}></section>`;
}

function resetConversation(clearInput) {
  state.answers = {};
  state.message = "";
  result.hidden = true;
  result.innerHTML = "";
  if (clearInput) messageInput.value = "";
  messageInput.focus();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  })[character]);
}
