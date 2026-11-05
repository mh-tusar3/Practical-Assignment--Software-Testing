"use strict";

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text; // textContent: never inject HTML
  return node;
}

function show(output, data, httpStatus) {
  output.replaceChildren();
  output.classList.remove("ok", "err");
  if (data.call) output.append(el("div", "call", data.call));
  if (data.ok) {
    output.classList.add("ok");
    const line = el("div", "value");
    line.append(el("span", "badge ok", "result"), el("code", "", data.result), el("span", "type", data.result_type));
    output.append(line);
  } else {
    output.classList.add("err");
    const line = el("div", "value");
    const label = httpStatus >= 400 ? "input problem" : "raised";
    line.append(el("span", "badge err", label), el("code", "", `${data.error_type}: ${data.error}`));
    output.append(line);
  }
}

async function runForm(form) {
  const name = form.dataset.name;
  const args = Array.from(form.querySelectorAll("input")).map((i) => i.value);
  const output = form.closest(".card").querySelector(".result");
  output.textContent = "running...";
  try {
    const res = await fetch(`/api/run/${encodeURIComponent(name)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ args }),
    });
    show(output, await res.json(), res.status);
  } catch (e) {
    show(output, { ok: false, error_type: "NetworkError", error: String(e) }, 599);
  }
}

document.querySelectorAll(".run-form").forEach((form) => {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    runForm(form);
  });
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const values = JSON.parse(chip.dataset.values);
    const form = chip.closest(".card").querySelector(".run-form");
    form.querySelectorAll("input").forEach((input, i) => { input.value = values[i]; });
    runForm(form);
  });
});

document.getElementById("run-all").addEventListener("click", () => {
  document.querySelectorAll(".card:not(.hidden) .run-form").forEach(runForm);
});

document.getElementById("filter").addEventListener("input", (event) => {
  const q = event.target.value.trim().toLowerCase();
  document.querySelectorAll(".card").forEach((card) => {
    const hit = card.dataset.name.includes(q) || card.dataset.group.includes(q);
    card.classList.toggle("hidden", !hit);
  });
});

async function refreshHealth() {
  const status = document.getElementById("health-status");
  const sha = document.getElementById("commit-sha");
  try {
    const res = await fetch("/health", { cache: "no-store" });
    const data = await res.json();
    status.textContent = data.status;
    status.className = data.status === "ok" ? "good" : "bad";
    sha.dataset.sha = data.commit;
    sha.textContent = data.commit === "unknown" ? data.commit : data.commit.slice(0, 7);
    sha.title = data.commit;
  } catch (e) {
    status.textContent = "unreachable";
    status.className = "bad";
  }
}
refreshHealth();
