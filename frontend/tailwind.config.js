/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        sucesso: "#10b981",
        erro: "#ef4444",
        alerta: "#fbbf24",
      },
    },
  },
  plugins: [],
};
