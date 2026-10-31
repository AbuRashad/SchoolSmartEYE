/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        night: "#101a2a",
        navy: "#18263b",
        cobalt: "#2c4262",
        sky: "#c5a66a",
        mist: "#f4f0e8",
        panel: "#1a2a40",
        critical: "#d96b68",
        warning: "#c5a66a",
        safe: "#78b69a",
        ivory: "#f4f0e8",
        gold: "#c5a66a",
        "gold-soft": "rgba(197, 166, 106, .14)",
        "panel-border": "rgba(197, 166, 106, .18)",
      },
      fontFamily: {
        sans: ["IBM Plex Sans Arabic", "Segoe UI", "Tahoma", "sans-serif"],
        display: ["Amiri", "IBM Plex Sans Arabic", "Georgia", "serif"],
      },
      boxShadow: {
        panel: "0 18px 60px rgba(3, 10, 22, 0.30)",
        elegant: "0 1px 0 rgba(197,166,106,.18), 0 14px 34px -18px rgba(3,10,22,.5)",
      },
      backgroundImage: {
        academic: "radial-gradient(circle at top left, rgba(197,166,106,.09), transparent 32%), radial-gradient(circle at bottom right, rgba(53,86,126,.16), transparent 38%), linear-gradient(145deg, #101a2a, #18263b 55%, #203653)",
      },
      borderRadius: {
        "sse": "1.25rem",
      },
    },
  },
  plugins: [],
};
