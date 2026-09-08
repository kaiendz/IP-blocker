/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          200: "#b3ccff",
          300: "#82abff",
          400: "#5285ff",
          500: "#2f5eff",
          600: "#1c40f0",
          700: "#1730c4",
          800: "#17299b",
          900: "#18277a",
        },
      },
    },
  },
  plugins: [],
};
