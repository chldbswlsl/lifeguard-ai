// 실수를 잡는 용도의 최소 규칙 (스타일 강제 X). product-admin / bp-portal 설정과 같은 방향.
import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import { defineConfig, globalIgnores } from "eslint/config";
import globals from "globals";
import tseslint from "typescript-eslint";

export default defineConfig([
  globalIgnores(["dist", "e2e-report"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    rules: {
      "@typescript-eslint/no-unused-vars": ["error", { args: "none", caughtErrors: "none", varsIgnorePattern: "^_" }],
      "no-empty": ["error", { allowEmptyCatch: true }], // 의도적으로 무시하는 catch {} 허용
      "@typescript-eslint/no-explicit-any": "off", // 응답 JSON 파싱 등 경계 지점에서만 사용
      // Context 파일은 Provider와 useX 훅을 같이 내보낸다
      "react-refresh/only-export-components": ["error", { allowExportNames: ["useAuth", "useUser", "useDialog"] }],
    },
  },
]);
