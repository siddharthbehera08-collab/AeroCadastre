import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: "#F4F1EA",
          subtle: "#EEEAE2",
          deep: "#E6E0D5",
        },
        surface: {
          DEFAULT: "#FAF8F3",
          pure: "#FFFFFF",
          warm: "#F5F2EB",
        },
        ink: {
          DEFAULT: "#171615",
          charcoal: "#24221F",
          espresso: "#302C28",
          muted: "#5C554E",
          faint: "#8C8277",
        },
        brown: {
          DEFAULT: "#6B5748",
          warm: "#8A735F",
          taupe: "#A18A76",
        },
        accent: {
          DEFAULT: "#B89A78",
          soft: "#C5AA8C",
          faint: "#E8DEC8",
        },
        sage: {
          DEFAULT: "#3D6B52",
          bg: "#EBF2EE",
          border: "#BDD4C6",
        },
        ochre: {
          DEFAULT: "#9E6B20",
          bg: "#F8F1E5",
          border: "#E5CFA8",
        },
        terracotta: {
          DEFAULT: "#9E3E37",
          bg: "#F9ECEB",
          border: "#E5B8B5",
        },
        line: {
          DEFAULT: "#E4DFD5",
          strong: "#D2C9BC",
          dark: "#3A3530",
        },
      },
      fontFamily: {
        serif: ["'Instrument Serif'", "'Newsreader'", "Georgia", "serif"],
        sans: ["'Plus Jakarta Sans'", "'Inter'", "system-ui", "-apple-system", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        editorial: "0 1px 3px rgba(23, 22, 21, 0.04), 0 8px 24px -4px rgba(23, 22, 21, 0.06)",
        elevated: "0 4px 12px rgba(23, 22, 21, 0.06), 0 20px 48px -12px rgba(23, 22, 21, 0.12)",
        subtle: "0 1px 2px rgba(23, 22, 21, 0.04)",
      },
      transitionTimingFunction: {
        smooth: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
