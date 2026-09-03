import type { PersonalApi } from "./personal-api";

/**
 * The renderer is shared; only the source of its API is environment-specific.
 * Keeping this envelope explicit makes it impossible for a production entrypoint
 * to accidentally select the browser fixture adapter.
 */
export interface PersonalAdapter {
  readonly kind: "preview" | "desktop";
  readonly synthetic: boolean;
  readonly api: PersonalApi;
}

export class PreviewAdapter implements PersonalAdapter {
  readonly kind = "preview" as const;
  readonly synthetic = true as const;

  constructor(readonly api: PersonalApi) {}
}

export class DesktopAdapter implements PersonalAdapter {
  readonly kind = "desktop" as const;
  readonly synthetic = false as const;

  constructor(readonly api: PersonalApi) {}
}

export type PersonalRendererInput = PersonalApi | PersonalAdapter;

export const unwrapPersonalApi = (input: PersonalRendererInput): PersonalApi =>
  "api" in input ? input.api : input;
