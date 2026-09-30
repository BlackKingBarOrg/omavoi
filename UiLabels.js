.pragma library

function mode(name, strings) {
  if (strings && ["default", "code", "prose", "terminal"].indexOf(name) >= 0)
    return strings.t("mode.name." + name)
  return name
}

function hotkey(name, strings) {
  return String(name || "").split("+").map(function(key) {
    var m = key.match(/^(RIGHT|LEFT)(CTRL|ALT|SHIFT|META)$/)
    if (m) {
      var keyName = { CTRL: "Ctrl", ALT: "Alt", SHIFT: "Shift", META: "Super" }[m[2]]
      return strings ? strings.tf(m[1] === "RIGHT" ? "key.right" : "key.left", keyName) : keyName
    }
    return key === "SCROLLLOCK" ? "Scroll Lock" : key
  }).join(" + ")
}
