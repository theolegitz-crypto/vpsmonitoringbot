/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Space Grotesk", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      colors: {
        panel: "#101826",
        panelSoft: "#172234",
        accent: "#45f0d1",
        accentWarm: "#f9a94b",
        success: "#22c55e",
        danger: "#ef4444",
        warning: "#facc15",
        quiet: "#6b7280",
        ink: "#e5eef9",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(69, 240, 209, 0.15), 0 20px 40px rgba(8, 15, 27, 0.35)",
      },
      backgroundImage: {
        mesh:
          "radial-gradient(circle at 20% 0%, rgba(69, 240, 209, 0.18), transparent 32%), radial-gradient(circle at 80% 20%, rgba(249, 169, 75, 0.14), transparent 28%), linear-gradient(180deg, #06101c 0%, #0c1422 52%, #09111b 100%)",
      },
    },
  },
  plugins: [],
};

