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

  it("exercises deterministic hypothesis rendering material with truthful provenance in the ACTIVE scenario", async () => {
    const api = createPersonalBrowserPreviewApi("ACTIVE");
    const exploration = await api.explorationGet("active");
    expect(exploration.hypotheses.length).toBeGreaterThan(0);
    for (const hypothesis of exploration.hypotheses) {
      expect(hypothesis.proposal_text).toBeTruthy();
      expect(hypothesis.uncertainty_text).toBeTruthy();
      expect(hypothesis.discriminator_text).toBeTruthy();
    }
    expect(exploration.hypotheses.some((item) => (item.context_refs ?? []).some((ref) => ref.source_turn_ids.length > 0))).toBe(true);
    expect(exploration.hypotheses.some((item) => !(item.context_refs ?? []).some((ref) => ref.source_turn_ids.length > 0))).toBe(true);
  });

  it("provides a synthetic-only SEARCH_MANY scenario matching the SearchView pagination contract", async () => {
    const api = createPersonalBrowserPreviewApi("SEARCH_MANY");
    const sessions = (await api.reflectionList()).sessions;
    expect(sessions).toHaveLength(1);
    expect(sessions[0]?.session_id).toBe("many");

    const filters = { state: "ALL" as const, content: "ALL" as const, period: "ALL" as const, formulationStatus: "ALL" as const };
    const first = await api.reflectionSearch("маршрут", filters, 20, 0);
    expect(first.total_matches).toBe(45);
    expect(first.results).toHaveLength(20);
    expect(first.has_more).toBe(true);
    expect(first.truncated).toBe(true);

    const second = await api.reflectionSearch("маршрут", filters, 20, 20);
    expect(second.results).toHaveLength(20);
    expect(second.has_more).toBe(true);
    expect(second.results.some((item) => first.results.some((row) => row.result_id === item.result_id))).toBe(false);

    const third = await api.reflectionSearch("маршрут", filters, 20, 40);
    expect(third.results).toHaveLength(5);
    expect(third.has_more).toBe(false);
    expect(third.truncated).toBe(false);
  });
});
