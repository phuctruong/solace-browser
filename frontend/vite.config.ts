import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/tests/setupTests.ts",
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary"],
      exclude: [
        "scripts/**",
        "src/setupTests.ts",
        "src/main.tsx",
        "src/types/**",
        "src/components/LoadingSpinner.tsx",
        "src/pages/AppDetailPage.tsx",
      ],
    },
  },
});
