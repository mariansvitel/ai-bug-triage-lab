const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
const form = document.querySelector("#bug-form");
const formMessage = document.querySelector("#form-message");
const verdictMessage = document.querySelector("#verdict-message");
const triageButton = document.querySelector("#triage-button");
const saveVerdictButton = document.querySelector("#save-verdict");
let currentEntry = null;
let currentReport = null;
let selectedVerdict = null;
let trackerIssues = [];

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

async function api(path, payload, method = "POST") {
  const response = await fetch(path, {
    method,
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

function trackerStatusLabel(status) {
  const labels = {
    inbox: "Inbox",
    investigating: "Investigating",
    planned: "Planned",
    resolved: "Resolved",
  };
  return labels[status] || status;
}

function renderTracker(data) {
  trackerIssues = data.issues;
  const summary = data.summary;
  document.querySelector("#tracker-total").textContent = String(summary.total);
  document.querySelector("#tracker-active").textContent = String(
    summary.statuses.investigating + summary.statuses.planned,
  );
  document.querySelector("#tracker-resolved").textContent = String(summary.statuses.resolved);
  document.querySelector("#tracker-confidence").textContent = `${Math.round(summary.average_confidence * 100)}%`;

  const selectedStatus = document.querySelector("#tracker-filter").value;
  const visibleIssues = trackerIssues.filter(
    (issue) => selectedStatus === "all" || issue.status === selectedStatus,
  );
  const list = document.querySelector("#tracker-list");
  const empty = document.querySelector("#tracker-empty");
  list.replaceChildren();
  empty.hidden = visibleIssues.length > 0;

  visibleIssues.forEach((issue) => {
    const card = document.createElement("article");
    card.className = "issue-card";

    const identity = document.createElement("div");
    identity.className = "issue-identity";
    const id = document.createElement("span");
    id.className = "issue-id";
    id.textContent = issue.report.id;
    const title = document.createElement("strong");
    title.textContent = issue.report.title;
    const summaryText = document.createElement("p");
    summaryText.textContent = issue.entry.result.summary;
    identity.append(id, title, summaryText);

    const signals = document.createElement("div");
    signals.className = "issue-signals";
    [
      issue.entry.result.severity,
      issue.entry.result.priority,
      `${Math.round(issue.entry.result.confidence * 100)}% confidence`,
      issue.entry.human_verdict || "pending review",
    ].forEach((value) => {
      const signal = document.createElement("span");
      signal.textContent = value;
      signals.append(signal);
    });

    const status = document.createElement("select");
    status.className = "status-select";
    status.setAttribute("aria-label", `Workflow state for ${issue.report.id}`);
    ["inbox", "investigating", "planned", "resolved"].forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = trackerStatusLabel(value);
      option.selected = issue.status === value;
      status.append(option);
    });
    status.addEventListener("change", async () => {
      status.disabled = true;
      try {
        await api(`/api/issues/${encodeURIComponent(issue.report.id)}`, { status: status.value }, "PATCH");
        await refreshTracker();
        setMessage(document.querySelector("#tracker-message"), "Workflow state bol uložený lokálne.", "success");
      } catch (error) {
        status.value = issue.status;
        setMessage(document.querySelector("#tracker-message"), error.message, "error");
      } finally {
        status.disabled = false;
      }
    });

    card.append(identity, signals, status);
    list.append(card);
  });
}

async function refreshTracker() {
  const response = await fetch("/api/issues", { headers: { Accept: "application/json" } });
  const data = await response.json().catch(() => ({ detail: "Neplatná odpoveď servera." }));
  if (!response.ok) throw new Error(data.detail || "Tracker sa nepodarilo načítať.");
  renderTracker(data);
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
    currentReport = reportFromForm();
    currentEntry = await api("/api/triage", currentReport);
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
  if (!currentEntry || !currentReport || !selectedVerdict) return;
  try {
    const data = await api("/api/verdict", {
      report: currentReport,
      entry: currentEntry,
      verdict: selectedVerdict,
      notes: document.querySelector("#human-notes").value,
    });
    setMessage(verdictMessage, `Verdikt „${data.verdict}“ bol uložený lokálne.`, "success");
    saveVerdictButton.disabled = true;
    await refreshTracker();
  } catch (error) {
    setMessage(verdictMessage, error.message, "error");
  }
});

document.querySelector("#tracker-filter").addEventListener("change", () => {
  renderTracker({
    issues: trackerIssues,
    summary: {
      total: trackerIssues.length,
      statuses: ["inbox", "investigating", "planned", "resolved"].reduce(
        (counts, status) => ({
          ...counts,
          [status]: trackerIssues.filter((issue) => issue.status === status).length,
        }),
        {},
      ),
      average_confidence: trackerIssues.length
        ? trackerIssues.reduce((sum, issue) => sum + issue.entry.result.confidence, 0) / trackerIssues.length
        : 0,
    },
  });
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

refreshTracker().catch((error) => {
  setMessage(document.querySelector("#tracker-message"), error.message, "error");
});
