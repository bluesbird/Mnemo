import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  // Not VITE_-prefixed, so the key stays in the dev server and out of the browser bundle.
  const adminApiKey =
    loadEnv(mode, ".", "").MS2_ADMIN_API_KEY ?? "dev-admin-key";

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": "http://localhost:8080",
        "/rag-api": {
          target: "http://localhost:8000",
          rewrite: (path: string) => path.replace(/^\/rag-api/, ""),
          configure: (proxy) => {
            // Vite applies `rewrite` before this event, so the prefix is already stripped.
            proxy.on("proxyReq", (proxyReq) => {
              if (proxyReq.path.startsWith("/api/v1/admin/")) {
                proxyReq.setHeader("X-API-Key", adminApiKey);
              }
            });
          },
        },
      },
    },
  };
});
