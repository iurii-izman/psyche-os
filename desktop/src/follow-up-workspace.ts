import type { ReturnCandidate } from "./return-workspace";

export interface FollowUpWorkspace {
  candidate: ReturnCandidate;
  provenance_label: string;
  source_state_label: string;
  suggested_title: string;
}

export function buildFollowUpWorkspace(candidate: ReturnCandidate): FollowUpWorkspace {
  return {
    candidate,
    provenance_label: candidate.provenance === "DERIVED" ? "Записано ранее · производное предложение" : candidate.provenance === "USER_AUTHORED" ? "Записано ранее · ваш текст / ваша отметка" : "Записано ранее",
    source_state_label: candidate.session_state === "CLOSED" ? "Закрыта · только чтение" : "Активна",
    suggested_title: "Новая запись"
  };
}
