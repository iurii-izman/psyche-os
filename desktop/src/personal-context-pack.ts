import type { SearchResult } from "./personal-api";

export const CONTEXT_PACK_LIMIT = 20;

export interface ContextPack {
  selected: SearchResult[];
  source_turns: Array<{ turn_id: string; sequence: number; created_at: string; content: string; session_title: string }>;
}

/** Build an owner-visible, in-memory view from exactly the selected search rows. */
export function buildContextPack(selected: SearchResult[]): ContextPack {
  if (selected.length > CONTEXT_PACK_LIMIT) throw new Error("CONTEXT_PACK_LIMIT");
  const sourceTurns = new Map<string, ContextPack["source_turns"][number]>();
  for (const item of selected) for (const turn of item.source_turns) {
    sourceTurns.set(turn.turn_id, { ...turn, session_title: item.session_title });
  }
  return { selected: [...selected], source_turns: [...sourceTurns.values()].sort((a, b) => a.created_at.localeCompare(b.created_at) || a.sequence - b.sequence) };
}
