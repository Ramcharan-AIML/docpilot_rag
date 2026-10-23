// Vite: the dev server (npm run dev, port 5173) and the build tool (npm run build -> dist/).
// In development, every /api request is passed to the FastAPI server on port 8000, so the
// browser sees ONE origin and no CORS setup is needed. In production FastAPI serves dist/.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8000" }, // 127.0.0.1, never localhost (IPv6 trap)
  },
});
