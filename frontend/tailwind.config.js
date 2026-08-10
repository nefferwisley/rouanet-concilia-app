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
        navy: {
          950: "#090d1f",
          900: "#0b1126",
          800: "#121a36",
          700: "#212e59",
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', "-apple-system", "sans-serif"],
      },
    },
  },
  plugins: [],
};
