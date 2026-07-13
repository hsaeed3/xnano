/* Render ANSI SGR emitted by client-side Python inside Pyodide output nodes. */
(function installPyodideAnsi(global) {
  "use strict";

  const ESCAPE_PATTERN = /\x1b\[[0-9;?]*[ -/]*[@-~]/g;
  const OSC_PATTERN = /\x1b\][^\x07]*(?:\x07|\x1b\\)/g;
  const ANSI_COLORS = [
    "#282a36",
    "#ff5555",
    "#50fa7b",
    "#ffb86c",
    "#6272a4",
    "#bd93f9",
    "#8be9fd",
    "#f8f8f2",
    "#6272a4",
    "#ff6e6e",
    "#69ff94",
    "#ffffa5",
    "#7b8ab8",
    "#d6acff",
    "#a4ffff",
    "#ffffff",
  ];

  function escapeHtml(value) {
    return value.replace(
      /[&<>"']/g,
      (character) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[character],
    );
  }

  function getIndexedColor(index) {
    if (index < 16) return ANSI_COLORS[index];
    if (index < 232) {
      const offset = index - 16;
      const red = Math.floor(offset / 36);
      const green = Math.floor((offset % 36) / 6);
      const blue = offset % 6;
      const channel = (value) => (value === 0 ? 0 : 55 + value * 40);
      return `rgb(${channel(red)}, ${channel(green)}, ${channel(blue)})`;
    }
    const gray = 8 + (index - 232) * 10;
    return `rgb(${gray}, ${gray}, ${gray})`;
  }

  function getSpanStyle(state) {
    let foreground = state.foreground;
    let background = state.background;
    if (state.inverse) {
      [foreground, background] = [
        background || "var(--md-code-bg-color)",
        foreground || "var(--md-code-fg-color)",
      ];
    }
    const styles = [];
    if (foreground) styles.push(`color:${foreground}`);
    if (background) styles.push(`background-color:${background}`);
    if (state.bold) styles.push("font-weight:700");
    if (state.dim) styles.push("opacity:.65");
    if (state.italic) styles.push("font-style:italic");
    if (state.underline && state.strike) {
      styles.push("text-decoration:underline line-through");
    } else if (state.underline) {
      styles.push("text-decoration:underline");
    } else if (state.strike) {
      styles.push("text-decoration:line-through");
    }
    if (state.hidden) styles.push("visibility:hidden");
    return styles.join(";");
  }

  function resetState(state) {
    Object.assign(state, {
      foreground: null,
      background: null,
      bold: false,
      dim: false,
      italic: false,
      underline: false,
      inverse: false,
      hidden: false,
      strike: false,
    });
  }

  function applySgr(state, parameters) {
    const codes = parameters === "" ? [0] : parameters.split(";").map(Number);
    for (let index = 0; index < codes.length; index += 1) {
      const code = codes[index];
      if (code === 0) resetState(state);
      else if (code === 1) state.bold = true;
      else if (code === 2) state.dim = true;
      else if (code === 3) state.italic = true;
      else if (code === 4) state.underline = true;
      else if (code === 7) state.inverse = true;
      else if (code === 8) state.hidden = true;
      else if (code === 9) state.strike = true;
      else if (code === 22) {
        state.bold = false;
        state.dim = false;
      } else if (code === 23) state.italic = false;
      else if (code === 24) state.underline = false;
      else if (code === 27) state.inverse = false;
      else if (code === 28) state.hidden = false;
      else if (code === 29) state.strike = false;
      else if (code >= 30 && code <= 37) state.foreground = ANSI_COLORS[code - 30];
      else if (code >= 90 && code <= 97) state.foreground = ANSI_COLORS[code - 82];
      else if (code === 39) state.foreground = null;
      else if (code >= 40 && code <= 47) state.background = ANSI_COLORS[code - 40];
      else if (code >= 100 && code <= 107) state.background = ANSI_COLORS[code - 92];
      else if (code === 49) state.background = null;
      else if ((code === 38 || code === 48) && codes[index + 1] === 5) {
        const color = getIndexedColor(codes[index + 2]);
        if (code === 38) state.foreground = color;
        else state.background = color;
        index += 2;
      } else if ((code === 38 || code === 48) && codes[index + 1] === 2) {
        const color = `rgb(${codes[index + 2]}, ${codes[index + 3]}, ${codes[index + 4]})`;
        if (code === 38) state.foreground = color;
        else state.background = color;
        index += 4;
      }
    }
  }

  function convertAnsiToHtml(value) {
    const input = value.replace(OSC_PATTERN, "");
    const state = {};
    resetState(state);
    let html = "";
    let offset = 0;
    let match;
    ESCAPE_PATTERN.lastIndex = 0;
    while ((match = ESCAPE_PATTERN.exec(input)) !== null) {
      const text = input.slice(offset, match.index);
      const style = getSpanStyle(state);
      const escaped = escapeHtml(text);
      html += style && text ? `<span style="${style}">${escaped}</span>` : escaped;
      if (match[0].endsWith("m")) applySgr(state, match[0].slice(2, -1));
      offset = ESCAPE_PATTERN.lastIndex;
    }
    const tail = input.slice(offset);
    const style = getSpanStyle(state);
    const escaped = escapeHtml(tail);
    html += style && tail ? `<span style="${style}">${escaped}</span>` : escaped;
    return html;
  }

  function renderOutput(output) {
    const value = output.textContent || "";
    if (!value.includes("\x1b")) return;
    output.innerHTML = convertAnsiToHtml(value);
  }

  const observed = new WeakSet();
  function observeOutput(output) {
    if (observed.has(output)) return;
    observed.add(output);
    new MutationObserver(() => renderOutput(output)).observe(output, {
      childList: true,
      characterData: true,
      subtree: true,
    });
    renderOutput(output);
  }

  function observePage(root) {
    root.querySelectorAll(".pyodide-output").forEach(observeOutput);
  }

  global.__xnanoAnsiToHtml = convertAnsiToHtml;
  if (typeof document === "undefined") return;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => observePage(document));
  } else {
    observePage(document);
  }
  if (typeof document$ !== "undefined") {
    document$.subscribe((root) => observePage(root));
  }
})(globalThis);
