const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
const form = document.querySelector("#bug-form");
const formMessage = document.querySelector("#form-message");
const verdictMessage = document.querySelector("#verdict-message");
const triageButton = document.querySelector("#triage-button");
const saveVerdictButton = document.querySelector("#save-verdict");
let currentEntry = null;
let selectedVerdict = null;

const sample = {
  id: "WEB-DEMO-001",
  title: "Checkout confirmation button stays disabled",
  description: "After changing the delivery address, checkout cannot continue.",
  steps_to_reproduce: ["Open checkout", "Change the delivery address", "Accept the terms"],
  expected_behavior: "The confirmation button becomes enabled.",
  actual_behavior: "The button remains disabled with no visible error.",
  environment: "Synthetic environment, Firefox on Windows 11",
};

function reportFromForm() {
  return {
    id: document.querySelector("#bug-id").value.trim(),
    title: document.querySelector("#title").value.trim(),
    description: document.querySelector("#description").value.trim(),
    steps_to_reproduce: document.querySelector("#steps").value.split("\n").map((v) => v.trim()).filter(Boolean),
    expected_behavior: document.querySelector("#expected").value.trim(),
    actual_behavior: document.querySelector("#actual").value.trim(),
    environment: document.querySelector("#environment").value.trim(),
  };
}

function fillForm(value) {
  document.querySelector("#bug-id").value = value.id;
  document.querySelector("#title").value = value.title;
  document.querySelector("#description").value = value.description;
  document.querySelector("#steps").value = value.steps_to_reproduce.join("\n");
  document.querySelector("#expected").value = value.expected_behavior;
  document.querySelector("#actual").value = value.actual_behavior;
  document.querySelector("#environment").value = value.environment;
}

async function api(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({ detail: "Neplatná odpoveď servera." }));
  if (!response.ok) throw new Error(data.detail || "Požiadavka zlyhala.");
  return data;
}

function setMessage(element, text, type = "") {
  element.textContent = text;
  element.className = `message ${type}`.trim();
}

function fillList(selector, items, fallback) {
  const list = document.querySelector(selector);
  list.replaceChildren();
  const values = items.length ? items : [fallback];
  values.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = value;
    list.append(item);
  });
}

function renderTags(items) {
  const list = document.querySelector("#label-list");
  list.replaceChildren();
  items.forEach((value) => {
    const tag = document.createElement("span");
    tag.className = "tag";
    tag.textContent = value;
    list.append(tag);
  });
}

function addFlag(container, text, alert = false) {
  const flag = document.createElement("span");
  flag.className = `flag${alert ? " alert" : ""}`;
  flag.textContent = text;
  container.append(flag);
}

function renderResult(entry) {
  const result = entry.result;
  document.querySelector("#empty-state").hidden = true;
  document.querySelector("#result-content").hidden = false;
  document.querySelector("#result-summary").textContent = result.summary;
  document.querySelector("#confidence-value").textContent = `${Math.round(result.confidence * 100)}%`;
  document.querySelector("#severity-value").textContent = result.severity;
  document.querySelector("#priority-value").textContent = result.priority;
  document.querySelector("#action-value").textContent = result.recommended_action.replaceAll("_", " ");
  document.querySelector("#sensitivity-value").textContent = result.data_sensitivity;
  document.querySelector("#rationale-value").textContent = result.rationale;
  document.querySelector("#model-badge").textContent = entry.model;
  renderTags(result.suggested_labels);
  fillList("#missing-list", result.missing_information, "AI neoznačila žiadne chýbajúce údaje.");
  fillList("#questions-list", result.follow_up_questions, "AI nenavrhla doplňujúcu otázku.");

  const flags = document.querySelector("#safety-flags");
  flags.replaceChildren();
  addFlag(flags, "Ľudská kontrola povinná");
  addFlag(flags, result.prompt_injection_detected ? "Prompt injection podozrenie" : "Bez prompt injection signálu", result.prompt_injection_detected);
  addFlag(flags, result.secret_exposure_suspected ? "Možný únik tajomstva" : "Bez signálu úniku tajomstva", result.secret_exposure_suspected);
  saveVerdictButton.disabled = true;
  selectedVerdict = null;
  document.querySelectorAll("[data-verdict]").forEach((button) => button.classList.remove("selected"));
}

document.querySelector("#load-sample").addEventListener("click", () => {
  fillForm(sample);
  setMessage(formMessage, "Syntetický príklad je pripravený.", "success");
});

document.querySelector("#validate-button").addEventListener("click", async () => {
  if (!form.reportValidity()) return;
  try {
    const data = await api("/api/validate", reportFromForm());
    const count = data.redactions.length;
    setMessage(formMessage, count ? `Dáta sú platné. Redakcia zachytila ${count} citlivé vzory.` : "Dáta sú platné. Nenašli sa citlivé vzory.", "success");
  } catch (error) {
    setMessage(formMessage, error.message, "error");
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  triageButton.disabled = true;
  triageButton.querySelector("span").textContent = "AI analyzuje…";
  setMessage(formMessage, "Report sa lokálne rediguje a bezpečne odosiela modelu.");
  try {
    currentEntry = await api("/api/triage", reportFromForm());
    renderResult(currentEntry);
    setMessage(formMessage, "Triage je hotová. Skontroluj návrh a pridaj ľudský verdikt.", "success");
  } catch (error) {
    setMessage(formMessage, error.message, "error");
  } finally {
    triageButton.disabled = false;
    triageButton.querySelector("span").textContent = "Spustiť AI triage";
  }
});

document.querySelectorAll("[data-verdict]").forEach((button) => {
  button.addEventListener("click", () => {
    selectedVerdict = button.dataset.verdict;
    document.querySelectorAll("[data-verdict]").forEach((item) => item.classList.toggle("selected", item === button));
    saveVerdictButton.disabled = !currentEntry;
  });
});

saveVerdictButton.addEventListener("click", async () => {
  if (!currentEntry || !selectedVerdict) return;
  try {
    const data = await api("/api/verdict", {
      entry: currentEntry,
      verdict: selectedVerdict,
      notes: document.querySelector("#human-notes").value,
    });
    setMessage(verdictMessage, `Verdikt „${data.verdict}“ bol uložený lokálne.`, "success");
    saveVerdictButton.disabled = true;
  } catch (error) {
    setMessage(verdictMessage, error.message, "error");
  }
});

fetch("/api/health")
  .then((response) => response.json())
  .then((health) => {
    const status = document.querySelector("#server-status");
    status.classList.add(health.api_key_configured ? "ready" : "error");
    status.querySelector("span:last-child").textContent = health.api_key_configured ? `Server pripravený · ${health.model}` : "Server beží · API kľúč chýba";
  })
  .catch(() => {
    const status = document.querySelector("#server-status");
    status.classList.add("error");
    status.querySelector("span:last-child").textContent = "Server nie je dostupný";
  });
