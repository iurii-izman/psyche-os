import eslint from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.ts"],
    languageOptions: { globals: { document: "readonly", window: "readonly", HTMLElement: "readonly" } },
    rules: { "@typescript-eslint/no-explicit-any": "error" }
  },
  { ignores: ["dist/**", "src-tauri/target/**"] }
);
