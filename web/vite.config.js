import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The page and the API are different ports during `npm run dev`.
// Proxying /api keeps the browser on one origin, so the API does not need CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
