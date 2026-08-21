import axe from "axe-core";
import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";

import type { DesktopApi, StatusView } from "../src/api";
import { mount } from "../src/main";
import { t } from "../src/i18n";

function syntheticStatus(locked = false): StatusView {
  return {
    locked,
    data_mode: "SYNTHETIC_ONLY",
    real_data_gate: "CLOSED",
    network: "OFFLINE_NO_LISTENER",
    privacy: { processing_location: "LOCAL_ONLY", cloud: "DISABLED", telemetry: "OFF" }
  };
}

function mockApi(locked = false): DesktopApi {
  let stateLocked = locked;
  return {
    status: vi.fn(async () => syntheticStatus(stateLocked)),
    unlock: vi.fn(async () => { stateLocked = false; return { session_token: "opaque-session" }; }),
    lock: vi.fn(async () => { stateLocked = true; return { locked: true }; }),
    correct: vi.fn(async () => ({ history_preserved: true, version_count: 2 })),
    planDeletion: vi.fn(async () => ({ plan_id: "plan-opaque", affected_counts: { observations: 1 }, external_limitations: ["External copies remain outside local control."] })),
    executeDeletion: vi.fn(async () => ({ receipt_id: "receipt-opaque", content_in_receipt: false })),
    backupStatus: vi.fn(async () => ({ state: "VERIFIED_SYNTHETIC", export_is_backup: false })),
    verifyBackup: vi.fn(async () => ({ verified: true, content_disclosed: false })),
    validateRecovery: vi.fn(async () => ({ candidate_id: "candidate-opaque", validated: true, activated: false, active_vault_preserved: true })),
    activateRecovery: vi.fn(async () => ({ activated: true, previous_vault_retained: true })),
    previewExport: vi.fn(async () => ({ preview_id: "export-opaque", purpose: "portability", audience: "owner", scope: "synthetic", encrypted: true, redacted: true, export_is_backup: false })),
    executeExport: vi.fn(async () => ({ export_id: "complete-opaque", purpose: "portability", audience: "owner", scope: "synthetic", encrypted: true, redacted: true, export_is_backup: false })),
    archiveOperate: vi.fn(async (operation: string) => operation === "DELETE_LAMP_SOURCE" ? ({ plan_id: "orchid-plan", mutated: false }) : ({ operation, fixture_pack: "e03_orchid_station_v1" })),
    archiveTimeline: vi.fn(async (temporalRole: string) => ({ selected_clock: temporalRole, items: [] })),
    archiveExplorer: vi.fn(async () => ({ notice: "Claims are proposals, not facts." })),
    archiveSnapshotDiff: vi.fn(async () => ({ changed: ["claim-lamp"], unresolved_contradictions: 1, completion_percentage: null })),
    archiveExecuteDeletion: vi.fn(async () => ({ receipt_id: "e03-receipt", content_in_receipt: false }))
  };
}

function byText(text: string): HTMLButtonElement {
  const found = [...document.querySelectorAll<HTMLButtonElement>("button")].find((node) => node.textContent === text);
  if (!found) throw new Error(`Missing button: ${text}`);
  return found;
}

async function click(node: HTMLElement): Promise<void> {
  node.click();
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("E02 bounded desktop UI", () => {
  it("T3 renders malicious synthetic markup as inert text", async () => {
    const api = mockApi(false);
    const canary = '<img src=x onerror="window.__pwned=1"><script>bad()</script>';
    vi.mocked(api.correct).mockResolvedValue({ current_text: canary, history_preserved: true });
    await mount(api);
    const replacement = document.querySelector<HTMLInputElement>("#replacement")!;
    const reason = document.querySelector<HTMLInputElement>("#correction-reason")!;
    replacement.value = canary;
    reason.value = "Synthetic correction";
    document.querySelector<HTMLFormElement>("section form")!.requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 0));
    const status = document.querySelector("#operation-status")!;
    expect(status.textContent).toContain(canary);
    expect(status.querySelector("script")).toBeNull();
    expect(status.querySelector("img")).toBeNull();
  });

  it("T4 requires a dry-run before deletion and returns focus", async () => {
    const api = mockApi(false);
    await mount(api);
    const confirm = byText(t("privacy.confirm"));
    expect(confirm.disabled).toBe(true);
    await click(byText(t("privacy.preview")));
    expect(confirm.disabled).toBe(false);
    expect(document.activeElement).toBe(confirm);
    await click(confirm);
    expect(api.executeDeletion).toHaveBeenCalledWith("plan-opaque", "DELETE SYNTHETIC RECORD");
    expect(document.querySelector("#operation-status")!.textContent).toContain("ограничени");
  });

  it("T5 keeps recovery validation separate from activation", async () => {
    const api = mockApi(false);
    await mount(api);
    const activate = byText(t("recovery.activate"));
    expect(activate.disabled).toBe(true);
    await click(byText(t("recovery.validate")));
    expect(activate.disabled).toBe(false);
    expect(document.querySelector("#operation-status")!.textContent).toContain("активное хранилище не изменено");
    await click(activate);
    expect(api.activateRecovery).toHaveBeenCalledWith("candidate-opaque", "ACTIVATE VALIDATED CANDIDATE");
  });

  it("T6 previews purpose, audience, scope and protection before export", async () => {
    const api = mockApi(false);
    await mount(api);
    (document.querySelector("#export-purpose") as HTMLInputElement).value = "portability";
    (document.querySelector("#export-audience") as HTMLInputElement).value = "owner";
    (document.querySelector("#export-scope") as HTMLInputElement).value = "synthetic";
    const form = (document.querySelector("#export-purpose") as HTMLInputElement).form!;
    form.requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelector("#operation-status")!.textContent).toContain("пока ничего не записано");
    const execute = byText(t("export.confirm"));
    expect(execute.disabled).toBe(false);
    await click(execute);
    expect(api.executeExport).toHaveBeenCalledWith("export-opaque", "EXPORT SYNTHETIC PACKAGE");
  });

  it("T7 has accessible names, associations, status semantics and no serious axe violations", async () => {
    await mount(mockApi(false));
    const result = await axe.run(document, { rules: { "color-contrast": { enabled: false } } });
    expect(result.violations).toEqual([]);
    expect(document.querySelector("#operation-status")?.getAttribute("aria-live")).toBe("polite");
    const stylesheet = readFileSync("src/styles.css", "utf8");
    expect(stylesheet).toContain("@media (prefers-reduced-motion: reduce)");
    for (const input of document.querySelectorAll<HTMLInputElement>("input[type=text], input[type=password]")) {
      expect(document.querySelector(`label[for="${input.id}"]`)).not.toBeNull();
    }
  });

  it("T7 unlock errors clear the secret and return focus to the field", async () => {
    const api = mockApi(true);
    vi.mocked(api.unlock).mockRejectedValue("UNLOCK_REJECTED");
    await mount(api);
    const secret = document.querySelector<HTMLInputElement>("#unlock-secret")!;
    secret.value = "synthetic-secret";
    secret.form!.requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(secret.value).toBe("");
    expect(document.activeElement).toBe(secret);
    expect(document.querySelector("#unlock-error")!.textContent).toContain(t("unlock.rejected"));
  });
});

describe("E03 bounded archive UI", () => {
  it("E03-T2/T7 requires an explicit clock and presents months-away return without pressure", async () => {
    const api = mockApi(false);
    await mount(api);
    const clock = document.querySelector<HTMLSelectElement>("#timeline-clock")!;
    expect([...clock.options].map((option) => option.value)).toEqual(["occurred", "observed", "reported", "recorded", "asserted"]);
    clock.value = "observed";
    await click(byText(t("explore.timeline")));
    expect(api.archiveTimeline).toHaveBeenCalledWith("observed");
    const copy = document.body.textContent!.toLowerCase();
    for (const forbidden of ["streak", "overdue", "you are behind", "completion percentage", "hurry", "reward"]) {
      expect(copy).not.toContain(forbidden);
    }
  });

  it("E03-T1/T6 exposes only fixed capture choices and focus-safe deletion confirmation", async () => {
    const api = mockApi(false);
    await mount(api);
    expect(document.querySelector("textarea")).toBeNull();
    expect(document.querySelector('input[type="file"]')).toBeNull();
    await click(byText(t("archive.captureReport")));
    expect(api.archiveOperate).toHaveBeenCalledWith("CAPTURE_LAMP_REPORT", "occurred_summer_2042", "desktop_001");
    const confirm = byText(t("canonical.confirm"));
    expect(confirm.disabled).toBe(true);
    await click(byText(t("canonical.preview")));
    expect(confirm.disabled).toBe(false);
    expect(document.activeElement).toBe(confirm);
    await click(confirm);
    expect(api.archiveExecuteDeletion).toHaveBeenCalledWith("orchid-plan", "DELETE ORCHID LAMP SOURCE");
  });
});
