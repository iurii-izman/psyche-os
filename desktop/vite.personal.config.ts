import { defineConfig } from "vitest/config";
import { resolve } from "node:path";

// A distinct root prevents the Personal renderer from importing the synthetic
// entry point or its provider/archive/action dependency graph.
export default defineConfig({
  root: "personal",
  clearScreen: false,
  build: { outDir: "../dist-personal", emptyOutDir: true, target: "es2022", sourcemap: false },
  resolve: { alias: { "@personal": resolve(__dirname, "src") } }
});
