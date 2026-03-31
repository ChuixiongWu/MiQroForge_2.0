/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Port type colors matching the design spec
        'port-physical': '#f59e0b',    // amber/orange — physical_quantity
        'port-software': '#3b82f6',    // blue — software_data_package
        'port-logic': '#22c55e',       // green — logic_value
        'port-report': '#a855f7',      // purple — report_object
        // ── Theme-aware semantic colors ──────────────────────────────────────
        mf: {
          base:  'rgb(var(--mf-bg-base) / <alpha-value>)',
          panel: 'rgb(var(--mf-bg-panel) / <alpha-value>)',
          card:  'rgb(var(--mf-bg-card) / <alpha-value>)',
          input: 'rgb(var(--mf-bg-input) / <alpha-value>)',
          hover: 'rgb(var(--mf-bg-hover) / <alpha-value>)',
        },
        'mf-text': {
          primary:   'rgb(var(--mf-text-primary) / <alpha-value>)',
          secondary: 'rgb(var(--mf-text-secondary) / <alpha-value>)',
          muted:     'rgb(var(--mf-text-muted) / <alpha-value>)',
        },
        'mf-border': 'rgb(var(--mf-border) / <alpha-value>)',
      },
    },
  },
  plugins: [],
}
