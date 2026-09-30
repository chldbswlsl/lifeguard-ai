import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// /api/... 요청을 백엔드로 넘긴다. 같은 주소에서 동작하므로 CORS 문제가 없다.
// e2e 테스트는 API_URL 환경변수로 테스트용 백엔드를 가리킨다.
const apiUrl = process.env.API_URL ?? "http://localhost:8000";
const proxy = {
  "/api": {
    target: apiUrl,
    rewrite: (path: string) => path.replace(/^\/api/, ""),
  },
};

export default defineConfig({
  plugins: [react()],
  server: { proxy },
  preview: { proxy },
});
