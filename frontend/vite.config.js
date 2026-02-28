/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: { "@": path.resolve(process.cwd(), "src") },
    },
    server: {
        port: 5173,
        proxy: {
            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true,
            },
            "/health": { target: "http://localhost:8000", changeOrigin: true },
        },
    },
    test: {
        environment: "jsdom",
        globals: true,
        include: ["src/**/*.{test,spec}.{ts,tsx}"],
        setupFiles: ["./src/test-setup.ts"],
        coverage: {
            provider: "v8",
            reporter: ["text", "lcov"],
            include: ["src/**/*.{ts,tsx}"],
            exclude: [
                "src/**/*.d.ts",
                "src/main.tsx",
                "src/vite-env.d.ts",
                "src/App.tsx",
                "src/**/*.test.*",
                "src/**/*.spec.*",
                "src/context/AuthContext.tsx",
                "src/pages/Login.tsx",
            ],
            thresholds: {
                statements: 35,
                lines: 35,
            },
        },
    },
});
