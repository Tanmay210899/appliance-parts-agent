/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'partselect-blue': '#0066CC',
        'partselect-dark': '#003366',
        'partselect-light': '#E6F2FF',
      },
    },
  },
  plugins: [],
}
