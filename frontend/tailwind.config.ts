import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        serif: ['"Times New Roman"', 'serif'],
      },
      colors: {
        'bg-page': '#F0EBE6',
        'bg-main': '#F7F4F1',
        'brand-black': '#1A1A1A',
        'text-primary': '#4A4A4A',
        'text-secondary': '#AEAEAE',
        'swirl-yellow': '#F9D49C',
        'swirl-green': '#C8DBC8',
        'swirl-purple': '#D8C8E0',
      },
      boxShadow: {
        'neumorphic-outer': '6px 6px 12px #e1ddd9, -6px -6px 12px #ffffff',
        'neumorphic-inner': 'inset 6px 6px 12px #e1ddd9, inset -6px -6px 12px #ffffff',
      }
    },
  },
  plugins: [],
};
export default config;