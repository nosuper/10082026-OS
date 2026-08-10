module.exports = {
  presets: [require("frappe-ui/tailwind")],
  content: [
    "./index.html",
    "./src/**/*.{vue,js}",
    "./node_modules/frappe-ui/src/components/**/*.{vue,js}",
  ],
}
