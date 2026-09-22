import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./contexts/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f7f8f8",
          100: "#eceeed",
          200: "#d9ddda",
          500: "#5d6761",
          700: "#2d3631",
          900: "#101412"
        },
        market: {
          green: "#00a862",
          mint: "#e8f7ef",
          blue: "#2557a7",
          red: "#d92d20"
        }
      },
      boxShadow: {
        lift: "0 12px 30px rgba(16, 20, 18, 0.08)"
      }
    }
  },
  plugins: []
};

export default config;
