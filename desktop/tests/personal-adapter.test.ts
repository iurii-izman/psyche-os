import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { PersonalApi } from "../src/personal-api";
import { DesktopAdapter, PreviewAdapter } from "../src/personal-adapter";
import { mountPersonal } from "../src/personal-renderer";

const source = (file: string) => readFileSync(resolve(process.cwd(), "src", file), "utf8");

describe("Personal renderer adapters", () => {
  it("keeps preview synthetic and desktop real", () => {
    const api = {} as PersonalApi;
    expect(new PreviewAdapter(api)).toMatchObject({ kind: "preview", synthetic: true, api });
    expect(new DesktopAdapter(api)).toMatchObject({ kind: "desktop", synthetic: false, api });
  });

  it("keeps the production entrypoint away from preview fixtures and provider commands in local mode", () => {
    const desktopEntry = source("personal-tauri.ts");
    const localApi = source("personal-local-api.ts");
    expect(desktopEntry).not.toContain("personal-browser-preview");
    expect(desktopEntry).not.toContain("personal-browser-preview-api");
    expect(localApi).not.toContain("desktop_ai_");
    expect(source("personal-browser-preview.ts")).toContain("PreviewAdapter");
    expect(source("personal-browser-preview.ts")).toContain("personal-renderer");
    expect(desktopEntry).toContain("personal-renderer");
  });

  it("does not touch provider capabilities during local startup", async () => {
    const providerReads: string[] = [];
    const api = new Proxy({
      status: async () => ({ runtime_profile: "LOCAL_PERSONAL" as const, real_data_gate: "CLOSED" as const, local_personal: "ADMITTED" as const, locked: false, inbound_listener: "NONE" as const, outbound_provider: "NOT_CONFIGURED" as const, network: "OFFLINE_NO_LISTENER" as const, privacy: { core_processing_location: "LOCAL" as const, cloud_storage: "DISABLED" as const, cloud_disclosure: "NEVER_CLOUD" as const, telemetry: "OFF" as const } }),
      reflectionList: async () => ({ sessions: [] }),
    }, { get(target, property, receiver) {
      if (String(property).startsWith("ai")) providerReads.push(String(property));
      return Reflect.get(target, property, receiver);
    } }) as unknown as PersonalApi;
    const host = document.querySelector<HTMLDivElement>("#app")!;
    await mountPersonal(new DesktopAdapter(api), host);
    expect(providerReads).toEqual([]);
    expect(document.body.textContent).toContain("Сегодня");
  });
});
