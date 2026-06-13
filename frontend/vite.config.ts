import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api to the FastAPI backend on :8137 so the frontend
// can use same-origin fetches in development and in the bundled production
// deploy (FastAPI serves the built assets).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8137",
    },
  },
  build: {
    outDir: "dist",
  },
});
