import { defineConfig } from "vitest/config";

export default defineConfig({
  clearScreen: false,
  server: { strictPort: true },
  build: { target: "es2022", sourcemap: false },
  test: { environment: "jsdom", setupFiles: ["./tests/setup.ts"] }
});
