import { defineConfig } from "vitest/config";
import { resolve } from "node:path";

export default defineConfig({
  root: "personal-preview",
  clearScreen: false,
  server: { host: "127.0.0.1", port: 1421, strictPort: true, fs: { allow: [resolve(__dirname)] } }
});
