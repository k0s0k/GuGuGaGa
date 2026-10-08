import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    // Toolchains and desktop bundles contain thousands of generated files.
    watch: { ignored: ["**/.local/**", "**/release/**"] },
    proxy: { "/api": "http://127.0.0.1:8766" },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("@codemirror/lang-cpp") || id.includes("@lezer/cpp"))
            return "language-cpp";
          if (
            id.includes("node_modules") &&
            (id.includes("@codemirror") ||
              id.includes("@lezer") ||
              id.includes("style-mod") ||
              id.includes("w3c-keyname") ||
              id.includes("crelt"))
          )
            return "editor-core";
        },
      },
    },
  },
});
