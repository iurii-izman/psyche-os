import { desktopApi, type DesktopApi, type StatusView } from "./api";

type Data = Record<string, unknown>;

function el<K extends keyof HTMLElementTagNameMap>(tag: K, text?: string): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}

function field(labelText: string, id: string, type = "text"): [HTMLLabelElement, HTMLInputElement] {
  const label = el("label", labelText);
  label.htmlFor = id;
  const input = el("input");
  input.id = id;
  input.name = id;
  input.type = type;
  return [label, input];
}

function button(text: string, action: () => Promise<void>, className = "secondary"): HTMLButtonElement {
  const node = el("button", text);
  node.type = "button";
  node.className = className;
  node.addEventListener("click", () => void action());
  return node;
}

function renderResult(region: HTMLElement, value: Data, message: string): void {
  region.replaceChildren();
  const heading = el("strong", message);
  region.append(heading);
  const list = el("dl");
  for (const [key, raw] of Object.entries(value)) {
    const dt = el("dt", key.replaceAll("_", " "));
    const dd = el("dd", typeof raw === "object" ? JSON.stringify(raw) : String(raw));
    list.append(dt, dd);
  }
  region.append(list);
}

function safeError(region: HTMLElement, error: unknown): void {
  const code = typeof error === "string" ? error : "OPERATION_FAILED";
  region.textContent = `The operation did not complete (${code.slice(0, 80)}). Existing state was preserved.`;
  region.focus();
}

export async function mount(api: DesktopApi = desktopApi): Promise<void> {
  const root = document.querySelector<HTMLDivElement>("#app");
  if (!root) throw new Error("APP_ROOT_MISSING");
  root.replaceChildren();

  const header = el("header");
  const brand = el("div");
  brand.className = "brand";
  brand.append(el("span", "PSYCHE OS"), el("small", "Local vault controls · synthetic profile"));
  const lockButton = button("Lock session", async () => {
    await api.lock();
    window.location.reload();
  });
  lockButton.id = "lock-session";
  header.append(brand, lockButton);

  const main = el("main");
  main.id = "main-content";
  main.tabIndex = -1;
  const statusRegion = el("section");
  statusRegion.className = "status-strip";
  statusRegion.setAttribute("aria-label", "Privacy and runtime status");
  const operationStatus = el("div");
  operationStatus.id = "operation-status";
  operationStatus.className = "result";
  operationStatus.setAttribute("role", "status");
  operationStatus.setAttribute("aria-live", "polite");
  operationStatus.tabIndex = -1;

  let status: StatusView;
  try {
    status = await api.status();
  } catch (error) {
    safeError(operationStatus, error);
    root.append(header, main, operationStatus);
    return;
  }

  for (const [label, value] of [
    ["Data", status.data_mode],
    ["Gate", status.real_data_gate],
    ["Runtime", status.network],
    ["Cloud", status.privacy.cloud]
  ]) {
    const item = el("div");
    item.append(el("span", label), el("strong", value));
    statusRegion.append(item);
  }

  if (status.locked) {
    lockButton.hidden = true;
    const unlock = el("section");
    unlock.className = "unlock card";
    unlock.append(el("p", "LOCAL / OFFLINE"), el("h1", "Unlock the synthetic vault"));
    unlock.append(el("p", "This demonstration accepts fictional repository-owned data only. Real data remains prohibited."));
    const form = el("form");
    const [secretLabel, secret] = field("Local session secret", "unlock-secret", "password");
    secret.autocomplete = "off";
    secret.maxLength = 256;
    secret.required = true;
    const error = el("p");
    error.id = "unlock-error";
    error.className = "field-error";
    secret.setAttribute("aria-describedby", error.id);
    const submit = el("button", "Unlock locally");
    submit.type = "submit";
    submit.className = "primary";
    form.append(secretLabel, secret, error, submit);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void api.unlock(secret.value).then(() => mount(api)).catch((reason: unknown) => {
        secret.value = "";
        error.textContent = `Unlock rejected (${String(reason).slice(0, 64)}).`;
        secret.focus();
      });
    });
    unlock.append(form);
    main.append(statusRegion, unlock);
    root.append(header, main, operationStatus);
    secret.focus();
    return;
  }

  const title = el("div");
  title.className = "hero";
  title.append(el("p", "PRIVATE BY ARCHITECTURE"), el("h1", "Your local control center"));
  title.append(el("p", "Correction preserves history. Deletion has limits. Restore validation never activates a vault."));

  const grid = el("div");
  grid.className = "grid";

  let operationSequence = 0;
  const archive = el("section");
  archive.className = "card archive-card";
  archive.append(el("p", "EVIDENCE ARCHIVE"), el("h2", "Orchid Station fixture"));
  archive.append(el("p", "Closed fictional capture only. Sources, reports, assertions, proposals, conflicts, and unknowns remain distinct."));
  const archiveAction = (label: string, operation: string, choice: string): HTMLButtonElement =>
    button(label, async () => {
      operationSequence += 1;
      try {
        const result = await api.archiveOperate(operation, choice, `desktop_${operationSequence.toString().padStart(3, "0")}`);
        renderResult(operationStatus, result, `${label} completed from the bundled fictional fixture.`);
      } catch (error) { safeError(operationStatus, error); }
    });
  archive.append(
    archiveAction("Capture lamp report", "CAPTURE_LAMP_REPORT", "occurred_summer_2042"),
    archiveAction("Capture lamp observation", "CAPTURE_LAMP_OBSERVATION", "observed_interval"),
    archiveAction("Capture counterreport", "CAPTURE_COUNTERREPORT", "occurred_unknown"),
    archiveAction("Assemble epistemic set", "ASSEMBLE_EPISTEMIC_SET", "descriptive_proposed"),
    archiveAction("Create baseline snapshot", "CREATE_BASELINE_SNAPSHOT", "baseline"),
    archiveAction("Create revised snapshot", "CREATE_REVISED_SNAPSHOT", "revised"),
    archiveAction("Correct report time canonically", "CORRECT_LAMP_REPORT_TIME", "corrected_reported_exact")
  );

  const explore = el("section");
  explore.className = "card";
  explore.append(el("p", "TIMELINE & EPISTEMICS"), el("h2", "Select a clock explicitly"));
  const clockLabel = el("label", "Timeline clock");
  clockLabel.htmlFor = "timeline-clock";
  const clock = el("select");
  clock.id = "timeline-clock";
  for (const role of ["occurred", "observed", "reported", "recorded", "asserted"]) {
    const option = el("option", role);
    option.value = role;
    clock.append(option);
  }
  const timelineButton = button("Load selected timeline", async () => {
    try { renderResult(operationStatus, await api.archiveTimeline(clock.value), `Timeline uses the ${clock.value} clock; fuzzy and unknown values remain explicit.`); }
    catch (error) { safeError(operationStatus, error); }
  });
  const explorerButton = button("Open evidence explorer", async () => {
    try { renderResult(operationStatus, await api.archiveExplorer(), "Explorer loaded. A proposal is not a fact or evidence."); }
    catch (error) { safeError(operationStatus, error); }
  });
  const diffButton = button("Compare model snapshots", async () => {
    try { renderResult(operationStatus, await api.archiveSnapshotDiff(), "Immutable deterministic snapshot change loaded; unresolved state remains visible."); }
    catch (error) { safeError(operationStatus, error); }
  });
  explore.append(clockLabel, clock, timelineButton, explorerButton, diffButton);

  const canonicalDeletion = el("section");
  canonicalDeletion.className = "card";
  canonicalDeletion.append(el("p", "CANONICAL DELETION"), el("h2", "Preview dependency closure"));
  canonicalDeletion.append(el("p", "Dry-run changes nothing. External copies and retained backups have stated limits."));
  let archivePlan = "";
  const archiveDeleteConfirm = button("Confirm canonical deletion", async () => {
    try {
      const result = await api.archiveExecuteDeletion(archivePlan, "DELETE ORCHID LAMP SOURCE");
      renderResult(operationStatus, result, "Canonical source and reconstructive descendants deleted; receipt contains no deleted content or stable content hash.");
      archiveDeleteConfirm.disabled = true;
      archiveDeletePreview.focus();
    } catch (error) { safeError(operationStatus, error); }
  }, "danger");
  archiveDeleteConfirm.disabled = true;
  const archiveDeletePreview = button("Preview canonical deletion", async () => {
    try {
      operationSequence += 1;
      const result = await api.archiveOperate("DELETE_LAMP_SOURCE", "dry_run", `desktop_delete_${operationSequence}`);
      archivePlan = String(result.plan_id ?? "");
      renderResult(operationStatus, result, "Canonical deletion dry-run only; no state changed.");
      archiveDeleteConfirm.disabled = !archivePlan;
      archiveDeleteConfirm.focus();
    } catch (error) { safeError(operationStatus, error); }
  });
  canonicalDeletion.append(archiveDeletePreview, archiveDeleteConfirm);

  const privacy = el("section");
  privacy.className = "card";
  privacy.append(el("p", "PRIVACY"), el("h2", "Correction and deletion"));
  const correctionForm = el("form");
  const [replacementLabel, replacement] = field("Corrected synthetic observation", "replacement");
  replacement.required = true;
  replacement.maxLength = 512;
  const [reasonLabel, reason] = field("Reason for correction", "correction-reason");
  reason.required = true;
  reason.maxLength = 512;
  const correctButton = el("button", "Preserve history and correct");
  correctButton.type = "submit";
  correctionForm.append(replacementLabel, replacement, reasonLabel, reason, correctButton);
  correctionForm.addEventListener("submit", (event) => {
    event.preventDefault();
    void api.correct(replacement.value, reason.value)
      .then((value) => renderResult(operationStatus, value, "Correction applied to this synthetic session; earlier session version preserved."))
      .catch((error: unknown) => safeError(operationStatus, error));
  });
  let deletionPlan = "";
  const deletePlanButton = button("Preview deletion scope", async () => {
    try {
      const result = await api.planDeletion();
      deletionPlan = String(result.plan_id ?? "");
      renderResult(operationStatus, result, "Deletion dry-run only; nothing deleted.");
      deleteExecuteButton.disabled = !deletionPlan;
      deleteExecuteButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  });
  const deleteExecuteButton = button("Confirm deletion", async () => {
    try {
      const result = await api.executeDeletion(deletionPlan, "DELETE SYNTHETIC RECORD");
      renderResult(operationStatus, result, "Synthetic-session deletion applied with stated limitations; no canonical record was changed.");
      deleteExecuteButton.disabled = true;
      deletePlanButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  }, "danger");
  deleteExecuteButton.disabled = true;
  privacy.append(correctionForm, el("hr"), deletePlanButton, deleteExecuteButton);

  const recovery = el("section");
  recovery.className = "card";
  recovery.append(el("p", "BACKUP & RECOVERY"), el("h2", "Verify before activation"));
  let candidateId = "";
  const backupButton = button("Check backup health", async () => {
    try { renderResult(operationStatus, await api.backupStatus(), "Backup status loaded."); }
    catch (error) { safeError(operationStatus, error); }
  });
  const verifyButton = button("Verify backup", async () => {
    try { renderResult(operationStatus, await api.verifyBackup(), "Backup verified without content disclosure."); }
    catch (error) { safeError(operationStatus, error); }
  });
  const validateButton = button("Validate isolated recovery", async () => {
    try {
      const result = await api.validateRecovery();
      candidateId = String(result.candidate_id ?? "");
      renderResult(operationStatus, result, "Candidate validated; active vault unchanged.");
      activateButton.disabled = !candidateId;
      activateButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  });
  const activateButton = button("Activate validated candidate", async () => {
    try {
      const result = await api.activateRecovery(candidateId, "ACTIVATE VALIDATED CANDIDATE");
      renderResult(operationStatus, result, "Validated candidate activated separately.");
      activateButton.disabled = true;
      validateButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  }, "primary");
  activateButton.disabled = true;
  recovery.append(backupButton, verifyButton, validateButton, activateButton);

  const exports = el("section");
  exports.className = "card";
  exports.append(el("p", "EXPORT"), el("h2", "Preview minimum disclosure"));
  const exportForm = el("form");
  const [purposeLabel, purpose] = field("Purpose", "export-purpose");
  const [audienceLabel, audience] = field("Audience", "export-audience");
  const [scopeLabel, scope] = field("Scope", "export-scope");
  purpose.required = audience.required = scope.required = true;
  purpose.maxLength = audience.maxLength = scope.maxLength = 512;
  const encryptedLabel = el("label");
  const encrypted = el("input");
  encrypted.type = "checkbox";
  encrypted.checked = true;
  encryptedLabel.append(encrypted, document.createTextNode(" Encrypt package"));
  const redactedLabel = el("label");
  const redacted = el("input");
  redacted.type = "checkbox";
  redacted.checked = true;
  redactedLabel.append(redacted, document.createTextNode(" Apply redaction"));
  const previewButton = el("button", "Preview export");
  previewButton.type = "submit";
  let previewId = "";
  const exportButton = button("Confirm synthetic export", async () => {
    try {
      const result = await api.executeExport(previewId, "EXPORT SYNTHETIC PACKAGE");
      renderResult(operationStatus, result, "Export completed. This is not a backup.");
      exportButton.disabled = true;
      previewButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  }, "primary");
  exportButton.disabled = true;
  exportForm.append(purposeLabel, purpose, audienceLabel, audience, scopeLabel, scope, encryptedLabel, redactedLabel, previewButton, exportButton);
  exportForm.addEventListener("submit", (event) => {
    event.preventDefault();
    void api.previewExport({ purpose: purpose.value, audience: audience.value, scope: scope.value, encrypted: encrypted.checked, redacted: redacted.checked })
      .then((result) => {
        previewId = String(result.preview_id ?? "");
        renderResult(operationStatus, result, "Export preview; nothing written yet.");
        exportButton.disabled = !previewId;
        exportButton.focus();
      })
      .catch((error: unknown) => safeError(operationStatus, error));
  });
  exports.append(exportForm);

  grid.append(privacy, recovery, exports, archive, explore, canonicalDeletion);
  main.append(statusRegion, title, grid, operationStatus);
  root.append(header, main);
}

if (!import.meta.env.VITEST) void mount();
