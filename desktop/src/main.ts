import { desktopApi, type DesktopApi, type StatusView } from "./api";
import { presentKey, presentValue, t, type TranslationKey } from "./i18n";

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
    const dt = el("dt", presentKey(key));
    const dd = el("dd", presentValue(raw));
    list.append(dt, dd);
  }
  region.append(list);
}

function safeError(region: HTMLElement, error: unknown): void {
  const code = typeof error === "string" ? error : "OPERATION_FAILED";
  region.textContent = t("error.operation", { code: code.slice(0, 80) });
  region.focus();
}

export async function mount(api: DesktopApi = desktopApi): Promise<void> {
  const root = document.querySelector<HTMLDivElement>("#app");
  if (!root) throw new Error("APP_ROOT_MISSING");
  root.replaceChildren();

  const header = el("header");
  const brand = el("div");
  brand.className = "brand";
  brand.append(el("span", "PSYCHE OS"), el("small", t("brand.subtitle")));
  const lockButton = button(t("session.lock"), async () => {
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
  statusRegion.setAttribute("aria-label", t("status.aria"));
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
    [t("status.data"), status.data_mode],
    [t("status.gate"), status.real_data_gate],
    [t("status.runtime"), status.network],
    [t("status.cloud"), status.privacy.cloud]
  ]) {
    const item = el("div");
    item.append(el("span", label), el("strong", presentValue(value)));
    statusRegion.append(item);
  }

  if (status.locked) {
    lockButton.hidden = true;
    const unlock = el("section");
    unlock.className = "unlock card";
    unlock.append(el("p", t("value.OFFLINE_NO_LISTENER")), el("h1", t("unlock.heading")));
    unlock.append(el("p", t("unlock.notice")));
    const form = el("form");
    const [secretLabel, secret] = field(t("unlock.secret"), "unlock-secret", "password");
    secret.autocomplete = "off";
    secret.maxLength = 256;
    secret.required = true;
    const error = el("p");
    error.id = "unlock-error";
    error.className = "field-error";
    secret.setAttribute("aria-describedby", error.id);
    const submit = el("button", t("unlock.submit"));
    submit.type = "submit";
    submit.className = "primary";
    form.append(secretLabel, secret, error, submit);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void api.unlock(secret.value).then(() => mount(api)).catch((reason: unknown) => {
        secret.value = "";
        error.textContent = `${t("unlock.rejected")} (${String(reason).slice(0, 64)}).`;
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
  title.append(el("p", t("hero.kicker")), el("h1", t("hero.heading")));
  title.append(el("p", t("hero.notice")));

  const grid = el("div");
  grid.className = "grid";

  let operationSequence = 0;
  const archive = el("section");
  archive.className = "card archive-card";
  archive.append(el("p", t("archive.kicker")), el("h2", t("archive.heading")));
  archive.append(el("p", t("archive.notice")));
  const archiveAction = (label: string, operation: string, choice: string): HTMLButtonElement =>
    button(label, async () => {
      operationSequence += 1;
      try {
        const result = await api.archiveOperate(operation, choice, `desktop_${operationSequence.toString().padStart(3, "0")}`);
        renderResult(operationStatus, result, `${label}. ${t("archive.completed")}`);
      } catch (error) { safeError(operationStatus, error); }
    });
  archive.append(
    archiveAction(t("archive.captureReport"), "CAPTURE_LAMP_REPORT", "occurred_summer_2042"),
    archiveAction(t("archive.captureObservation"), "CAPTURE_LAMP_OBSERVATION", "observed_interval"),
    archiveAction(t("archive.captureCounterreport"), "CAPTURE_COUNTERREPORT", "occurred_unknown"),
    archiveAction(t("archive.assemble"), "ASSEMBLE_EPISTEMIC_SET", "descriptive_proposed"),
    archiveAction(t("archive.baseline"), "CREATE_BASELINE_SNAPSHOT", "baseline"),
    archiveAction(t("archive.revised"), "CREATE_REVISED_SNAPSHOT", "revised"),
    archiveAction(t("archive.correctTime"), "CORRECT_LAMP_REPORT_TIME", "corrected_reported_exact")
  );

  const explore = el("section");
  explore.className = "card";
  explore.append(el("p", t("explore.kicker")), el("h2", t("explore.heading")));
  const clockLabel = el("label", t("explore.clock"));
  clockLabel.htmlFor = "timeline-clock";
  const clock = el("select");
  clock.id = "timeline-clock";
  for (const role of ["occurred", "observed", "reported", "recorded", "asserted"]) {
    const option = el("option", t(`clock.${role}` as TranslationKey));
    option.value = role;
    clock.append(option);
  }
  const timelineButton = button(t("explore.timeline"), async () => {
    try { renderResult(operationStatus, await api.archiveTimeline(clock.value), t("explore.timelineResult", { clock: t(`clock.${clock.value}` as TranslationKey) })); }
    catch (error) { safeError(operationStatus, error); }
  });
  const explorerButton = button(t("explore.open"), async () => {
    try { renderResult(operationStatus, await api.archiveExplorer(), t("explore.openResult")); }
    catch (error) { safeError(operationStatus, error); }
  });
  const diffButton = button(t("explore.diff"), async () => {
    try { renderResult(operationStatus, await api.archiveSnapshotDiff(), t("explore.diffResult")); }
    catch (error) { safeError(operationStatus, error); }
  });
  explore.append(clockLabel, clock, timelineButton, explorerButton, diffButton);

  const canonicalDeletion = el("section");
  canonicalDeletion.className = "card";
  canonicalDeletion.append(el("p", t("canonical.kicker")), el("h2", t("canonical.heading")));
  canonicalDeletion.append(el("p", t("canonical.notice")));
  let archivePlan = "";
  const archiveDeleteConfirm = button(t("canonical.confirm"), async () => {
    try {
      const result = await api.archiveExecuteDeletion(archivePlan, "DELETE ORCHID LAMP SOURCE");
      renderResult(operationStatus, result, t("canonical.complete"));
      archiveDeleteConfirm.disabled = true;
      archiveDeletePreview.focus();
    } catch (error) { safeError(operationStatus, error); }
  }, "danger");
  archiveDeleteConfirm.disabled = true;
  const archiveDeletePreview = button(t("canonical.preview"), async () => {
    try {
      operationSequence += 1;
      const result = await api.archiveOperate("DELETE_LAMP_SOURCE", "dry_run", `desktop_delete_${operationSequence}`);
      archivePlan = String(result.plan_id ?? "");
      renderResult(operationStatus, result, t("canonical.previewResult"));
      archiveDeleteConfirm.disabled = !archivePlan;
      archiveDeleteConfirm.focus();
    } catch (error) { safeError(operationStatus, error); }
  });
  canonicalDeletion.append(archiveDeletePreview, archiveDeleteConfirm);

  const privacy = el("section");
  privacy.className = "card";
  privacy.append(el("p", t("privacy.kicker")), el("h2", t("privacy.heading")));
  const correctionForm = el("form");
  const [replacementLabel, replacement] = field(t("privacy.replacement"), "replacement");
  replacement.required = true;
  replacement.maxLength = 512;
  const [reasonLabel, reason] = field(t("privacy.reason"), "correction-reason");
  reason.required = true;
  reason.maxLength = 512;
  const correctButton = el("button", t("privacy.correct"));
  correctButton.type = "submit";
  correctionForm.append(replacementLabel, replacement, reasonLabel, reason, correctButton);
  correctionForm.addEventListener("submit", (event) => {
    event.preventDefault();
    void api.correct(replacement.value, reason.value)
      .then((value) => renderResult(operationStatus, value, t("privacy.correctResult")))
      .catch((error: unknown) => safeError(operationStatus, error));
  });
  let deletionPlan = "";
  const deletePlanButton = button(t("privacy.preview"), async () => {
    try {
      const result = await api.planDeletion();
      deletionPlan = String(result.plan_id ?? "");
      renderResult(operationStatus, result, t("privacy.previewResult"));
      deleteExecuteButton.disabled = !deletionPlan;
      deleteExecuteButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  });
  const deleteExecuteButton = button(t("privacy.confirm"), async () => {
    try {
      const result = await api.executeDeletion(deletionPlan, "DELETE SYNTHETIC RECORD");
      renderResult(operationStatus, result, t("privacy.complete"));
      deleteExecuteButton.disabled = true;
      deletePlanButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  }, "danger");
  deleteExecuteButton.disabled = true;
  privacy.append(correctionForm, el("hr"), deletePlanButton, deleteExecuteButton);

  const recovery = el("section");
  recovery.className = "card";
  recovery.append(el("p", t("recovery.kicker")), el("h2", t("recovery.heading")));
  let candidateId = "";
  const backupButton = button(t("recovery.health"), async () => {
    try { renderResult(operationStatus, await api.backupStatus(), t("recovery.healthResult")); }
    catch (error) { safeError(operationStatus, error); }
  });
  const verifyButton = button(t("recovery.verify"), async () => {
    try { renderResult(operationStatus, await api.verifyBackup(), t("recovery.verifyResult")); }
    catch (error) { safeError(operationStatus, error); }
  });
  const validateButton = button(t("recovery.validate"), async () => {
    try {
      const result = await api.validateRecovery();
      candidateId = String(result.candidate_id ?? "");
      renderResult(operationStatus, result, t("recovery.validateResult"));
      activateButton.disabled = !candidateId;
      activateButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  });
  const activateButton = button(t("recovery.activate"), async () => {
    try {
      const result = await api.activateRecovery(candidateId, "ACTIVATE VALIDATED CANDIDATE");
      renderResult(operationStatus, result, t("recovery.activateResult"));
      activateButton.disabled = true;
      validateButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  }, "primary");
  activateButton.disabled = true;
  recovery.append(backupButton, verifyButton, validateButton, activateButton);

  const exports = el("section");
  exports.className = "card";
  exports.append(el("p", t("export.kicker")), el("h2", t("export.heading")));
  const exportForm = el("form");
  const [purposeLabel, purpose] = field(t("export.purpose"), "export-purpose");
  const [audienceLabel, audience] = field(t("export.audience"), "export-audience");
  const [scopeLabel, scope] = field(t("export.scope"), "export-scope");
  purpose.required = audience.required = scope.required = true;
  purpose.maxLength = audience.maxLength = scope.maxLength = 512;
  const encryptedLabel = el("label");
  const encrypted = el("input");
  encrypted.type = "checkbox";
  encrypted.checked = true;
  encryptedLabel.append(encrypted, document.createTextNode(` ${t("export.encrypt")}`));
  const redactedLabel = el("label");
  const redacted = el("input");
  redacted.type = "checkbox";
  redacted.checked = true;
  redactedLabel.append(redacted, document.createTextNode(` ${t("export.redact")}`));
  const previewButton = el("button", t("export.preview"));
  previewButton.type = "submit";
  let previewId = "";
  const exportButton = button(t("export.confirm"), async () => {
    try {
      const result = await api.executeExport(previewId, "EXPORT SYNTHETIC PACKAGE");
      renderResult(operationStatus, result, t("export.complete"));
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
        renderResult(operationStatus, result, t("export.previewResult"));
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
