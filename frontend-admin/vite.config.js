import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
export default defineConfig({
    plugins: [react()],
    resolve: { alias: { "@": path.resolve(process.cwd(), "src") } },
    server: {
        port: 5174,
        proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } },
    },
});
