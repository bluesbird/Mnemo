import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "happy-dom",
    restoreMocks: true,
  },
  server: {
    proxy: {
      "/api": "http://localhost:8080",
      "/rag-api": {
        target: "http://localhost:8000",
        rewrite: (path: string) => path.replace(/^\/rag-api/, ""),
      },
    },
  },
});
