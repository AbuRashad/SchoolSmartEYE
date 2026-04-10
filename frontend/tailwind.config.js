/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        night: "#07111f",
        navy: "#0f2747",
        cobalt: "#1d4f91",
        sky: "#4f8fd8",
        mist: "#dfeafb",
        panel: "#0d1b31",
        critical: "#e84d5b",
        warning: "#ffb84d",
        safe: "#46c37b",
      },
      fontFamily: {
        sans: ["Space Grotesk", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        panel: "0 18px 60px rgba(3, 10, 22, 0.36)",
      },
      backgroundImage: {
        academic: "radial-gradient(circle at top left, rgba(79, 143, 216, 0.18), transparent 30%), radial-gradient(circle at bottom right, rgba(29, 79, 145, 0.18), transparent 30%), linear-gradient(145deg, #07111f, #0d1b31 45%, #143059)",
      },
    },
  },
  plugins: [],
};