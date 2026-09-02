import { defineConfig } from "vitest/config";
import { resolve } from "node:path";

const openai = process.env.PSYCHE_OS_PERSONAL_PROFILE_ID === "local_personal_bounded_openai_reflection_windows_v1" || process.env.PSYCHE_OS_PERSONAL_PROFILE_ID === "local_personal_ai_interview_openai_windows_v1";

// A distinct root prevents the Personal renderer from importing the synthetic
// entry point or its provider/archive/action dependency graph.
export default defineConfig({
  root: "personal",
  clearScreen: false,
  build: { outDir: "../dist-personal", emptyOutDir: true, target: "es2022", sourcemap: false },
  resolve: { alias: { "@personal": resolve(__dirname, "src") } },
  define: { __PERSONAL_OPENAI__: JSON.stringify(openai) },
});
