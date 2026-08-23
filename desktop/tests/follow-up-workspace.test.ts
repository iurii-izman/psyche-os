import { describe, expect, it } from "vitest";
import { buildFollowUpWorkspace } from "../src/follow-up-workspace";

describe("V3-F follow-up projection", () => {
  it("keeps historical provenance explicit and uses only a neutral editable-title suggestion", () => {
    const view = buildFollowUpWorkspace({ id: "formulation-1", category: "CURRENT_FORMULATION", session_id: "source", session_title: "Исходная", session_state: "CLOSED", text: "Производный текст", recorded_at: "2026-01-01T00:00:00Z", state: "CURRENT", source_anchors: [], provenance: "DERIVED" });
    expect(view).toMatchObject({ provenance_label: "Записано ранее · производное предложение", source_state_label: "Закрыта · только чтение", suggested_title: "Новая запись" });
    expect(JSON.stringify(view)).not.toMatch(/urgent|recommend|rank|score/i);
  });
});
