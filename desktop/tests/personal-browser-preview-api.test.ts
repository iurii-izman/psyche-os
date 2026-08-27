import { describe, expect, it } from "vitest";
import { createPersonalBrowserPreviewApi } from "../src/personal-browser-preview-api";

describe("Personal browser preview API", () => {
  it("supplies an in-memory ACTIVE scenario with synthetic exploration, AI, search, and longitudinal material", async () => {
    const api = createPersonalBrowserPreviewApi("ACTIVE");
    const sessions = (await api.reflectionList()).sessions;
    expect(sessions.map((item) => item.state)).toEqual(["ACTIVE", "CLOSED"]);
    expect(sessions.flatMap((item) => item.turns ?? [])).toHaveLength(4);

    const exploration = await api.explorationGet("active");
    expect(exploration.context.map((item) => item.kind)).toEqual(expect.arrayContaining(["UNKNOWN", "CONTRADICTION"]));
    expect(exploration.formulations.map((item) => item.status)).toEqual(expect.arrayContaining(["CURRENT", "PROPOSED", "SUPERSEDED"]));
    expect(exploration.formulations.find((item) => item.origin === "AI")?.ai_provenance?.actual_model).toBe("no-network");

    const search = await api.reflectionSearch("пауза", { state: "ALL", content: "ALL", period: "ALL", formulationStatus: "ALL" });
    expect(search.results.some((item) => item.related_context.length > 0)).toBe(true);
  });

  it("provides explicit CLOSED and EMPTY scenarios without admission, vault, or network state", async () => {
    const closed = createPersonalBrowserPreviewApi("CLOSED");
    expect((await closed.status()).network).toBe("OFFLINE_NO_LISTENER");
    expect((await closed.reflectionList()).sessions.map((item) => item.state)).toEqual(["CLOSED"]);
    expect((await closed.explorationGet("closed")).formulations[0]?.status).toBe("CURRENT");

    const empty = createPersonalBrowserPreviewApi("EMPTY");
    expect((await empty.reflectionList()).sessions).toEqual([]);
    expect((await empty.status()).admission_expires_at).toBeUndefined();
    expect((await empty.aiProviderStatus()).configured).toBe(false);
  });
});
