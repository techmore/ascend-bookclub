/* Shared Tailwind Play-CDN config for every page.
   Colours point at the CSS variables in assets/site.css so the same utility
   classes work in light and dark mode. Load after the Tailwind CDN script. */
(function () {
  function scale(name, steps) {
    var out = {};
    steps.forEach(function (s) { out[s] = "oklch(var(--" + name + "-" + s + ") / <alpha-value>)"; });
    return out;
  }
  window.tailwind = window.tailwind || {};
  window.tailwind.config = {
    darkMode: "media",
    theme: {
      extend: {
        colors: {
          olive: scale("olive", [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]),
          stone: scale("stone", [50, 100, 200, 300, 400, 500, 600, 700, 800, 900])
        },
        fontFamily: {
          display: ["Instrument Serif", "serif"],
          sans: ["Inter", "system-ui", "sans-serif"]
        }
      }
    }
  };
})();
