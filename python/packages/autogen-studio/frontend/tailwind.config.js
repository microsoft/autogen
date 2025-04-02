/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    `./src/pages/**/*.{js,jsx,ts,tsx}`,
    `./src/components/**/*.{js,jsx,ts,tsx}`,
  ],
  theme: {
    extend: {
      typography: {
        DEFAULT: {
          css: {
            maxWidth: "100ch",
          },
        },
      },
      transitionProperty: {
        height: "height",
        spacing: "margin, padding",
      },
      colors: {
        primary: "var(--color-bg-primary)",
        secondary: "var(--color-bg-secondary)",
        accent: "var(--color-bg-accent)",
        light: "var(--color-bg-light)",
        tertiary: "var(--color-bg-tertiary)",
      },
      textColor: {
        accent: "var(--color-text-accent)",
        primary: "var(--color-text-primary)",
        secondary: "var(--color-text-secondary)",
      },
      borderColor: {
        accent: "var(--color-border-accent)",
        primary: "var(--color-border-primary)",
        secondary: "var(--color-border-secondary)",
      },
      ringColor: {
        accent: "var(--color-text-accent)",
        primary: "var(--color-text-primary)",
        secondary: "var(--color-text-secondary)",
      },
    },
  },
  plugins: [
    require("@tailwindcss/typography"),
    function ({ addBase, theme }) {
      addBase({
        ":root": {
          "--tw-bg-opacity": "1",
          "--tw-text-opacity": "1",
          "--tw-border-opacity": "1",
        },
      });
    },
  ],
};
