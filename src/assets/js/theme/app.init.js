// Get saved theme from localStorage (Preline uses 'hs_theme')
var savedTheme = null;
try {
  savedTheme = localStorage.getItem('hs_theme') || localStorage.getItem('hsColorMode') || localStorage.getItem('theme');
} catch (e) {
  // localStorage not available, use default
}

var userSettings = {
  Layout: "vertical", // vertical | horizontal
  SidebarType: "full", // full | mini-sidebar
  BoxedLayout: false, // true | false
  Direction: "ltr", // ltr | rtl
  Theme: savedTheme === 'dark' ? "dark" : "light", // light | dark - respect Preline's saved preference
  ColorTheme: "Green_Theme", // Blue_Theme | Aqua_Theme | Purple_Theme | Green_Theme | Cyan_Theme | Orange_Theme
  cardBorder: false, // true | false
};
