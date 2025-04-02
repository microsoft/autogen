var version = DOCUMENTATION_OPTIONS.VERSION;
if (version === "stable") {
  var styles = `
#bd-header-version-warning {
  display: none;
}
  `
  var styleSheet = document.createElement("style")
  styleSheet.textContent = styles
  document.head.appendChild(styleSheet)
}