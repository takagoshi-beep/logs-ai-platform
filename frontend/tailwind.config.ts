import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./hooks/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#f4f7fb",
        panel: "#ffffff",
        ink: "#1f2937",
        sub: "#6b7280",
        accent: "#0f766e",
        warn: "#b45309",
        danger: "#b91c1c"
      }
    }
  },
  plugins: [],
};

export default config;
