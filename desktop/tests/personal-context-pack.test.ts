import { describe, expect, it } from "vitest";
import { buildContextPack, CONTEXT_PACK_LIMIT } from "../src/personal-context-pack";
import type { SearchResult } from "../src/personal-api";

const result = (id: string, turnId = "turn-1"): SearchResult => ({
  result_id: id, result_type: "FORMULATION", session_id: "session-1", session_title: "Synthetic reflection", session_state: "ACTIVE", at: "2026-08-20T12:00:00Z", text: `Synthetic ${id}`, excerpt: `Synthetic ${id}`, turn_id: null, turn_sequence: null, status: "CURRENT", source_turns: [{ turn_id: turnId, sequence: 1, created_at: "2026-08-20T12:00:00Z", content: "Exact synthetic source" }], why_here: "Формулировка опирается на одной вашей записи.", parent_result_id: null, ai_provenance: null, related_context: []
});

describe("Personal context pack", () => {
  it("contains exactly selected results and their direct source provenance", () => {
    const chosen = result("formulation:selected");
    const unrelated = result("formulation:unrelated", "turn-2");
    const pack = buildContextPack([chosen]);
    expect(pack.selected).toEqual([chosen]);
    expect(pack.selected).not.toContain(unrelated);
    expect(pack.source_turns).toEqual([{ ...chosen.source_turns[0], session_title: "Synthetic reflection" }]);
  });

  it("deduplicates exact provenance and rejects a pack over the local bound", () => {
    const first = result("first"); const second = result("second");
    expect(buildContextPack([first, second]).source_turns).toHaveLength(1);
    expect(() => buildContextPack(Array.from({ length: CONTEXT_PACK_LIMIT + 1 }, (_, index) => result(String(index), String(index))))).toThrow("CONTEXT_PACK_LIMIT");
  });
});
