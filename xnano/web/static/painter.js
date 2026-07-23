// xnano web painter: draws streamed terminal cells to a <canvas> and
// sends key/mouse/resize events back to the server. No dependencies.
//
// Frame wire shape (see xnano/web/frame.py):
//   { w, h, full, rows: { "y": [[text, fg, bg, mods], ...] }, cursor }
// A span's fg/bg are "#rrggbb" or null (terminal default); mods is a
// bitfield: bold=1 dim=2 italic=4 underline=8 reversed=16.

(function () {
  "use strict";

  var MOD_BOLD = 1, MOD_DIM = 2, MOD_ITALIC = 4,
      MOD_UNDERLINE = 8, MOD_REVERSED = 16;
  var DEFAULT_FG = "#d0d0d0";
  var DEFAULT_BG = "#101010";
  var FONT_SIZE = 16;
  var LINE_HEIGHT = 1.25;
  var FONT_FAMILY =
    "'SFMono-Regular', 'Menlo', 'Consolas', 'Liberation Mono', monospace";

  var canvas = document.getElementById("xnano");
  var ctx = canvas.getContext("2d");
  var dpr = window.devicePixelRatio || 1;

  var cellW = 0, cellH = 0;
  var cols = 0, rows = 0;
  var model = [];          // model[y] = array of spans
  var cursor = null;       // [x, y] or null

  function measureCell() {
    ctx.font = FONT_SIZE + "px " + FONT_FAMILY;
    cellW = Math.ceil(ctx.measureText("M").width);
    cellH = Math.ceil(FONT_SIZE * LINE_HEIGHT);
  }

  function gridSize() {
    var w = Math.max(1, Math.floor(window.innerWidth / cellW));
    var h = Math.max(1, Math.floor(window.innerHeight / cellH));
    return [w, h];
  }

  function resizeCanvas() {
    canvas.width = window.innerWidth * dpr;
    canvas.height = window.innerHeight * dpr;
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.textBaseline = "top";
  }

  function applyFrame(frame) {
    if (frame.full) {
      cols = frame.w;
      rows = frame.h;
      model = new Array(rows);
      for (var y = 0; y < rows; y++) { model[y] = []; }
    }
    for (var key in frame.rows) {
      if (frame.rows.hasOwnProperty(key)) {
        model[parseInt(key, 10)] = frame.rows[key];
      }
    }
    cursor = frame.cursor;
    paint();
  }

  function paint() {
    ctx.fillStyle = DEFAULT_BG;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (var y = 0; y < model.length; y++) {
      var spans = model[y];
      var x = 0;
      for (var i = 0; i < spans.length; i++) {
        x = paintSpan(spans[i], x, y);
      }
    }
    if (cursor) { paintCursor(cursor[0], cursor[1]); }
  }

  function paintSpan(span, x, y) {
    var text = span[0], fg = span[1] || DEFAULT_FG, bg = span[2], mods = span[3];
    if (mods & MOD_REVERSED) { var t = fg; fg = bg || DEFAULT_BG; bg = t; }
    var px = x * cellW, py = y * cellH;
    var width = text.length * cellW;
    if (bg) {
      ctx.fillStyle = bg;
      ctx.fillRect(px, py, width, cellH);
    }
    var weight = (mods & MOD_BOLD) ? "bold " : "";
    var style = (mods & MOD_ITALIC) ? "italic " : "";
    ctx.font = style + weight + FONT_SIZE + "px " + FONT_FAMILY;
    ctx.globalAlpha = (mods & MOD_DIM) ? 0.6 : 1.0;
    ctx.fillStyle = fg;
    ctx.fillText(text, px, py + (cellH - FONT_SIZE) / 2);
    ctx.globalAlpha = 1.0;
    if (mods & MOD_UNDERLINE) {
      ctx.strokeStyle = fg;
      ctx.beginPath();
      ctx.moveTo(px, py + cellH - 1);
      ctx.lineTo(px + width, py + cellH - 1);
      ctx.stroke();
    }
    return x + text.length;
  }

  function paintCursor(x, y) {
    ctx.fillStyle = DEFAULT_FG;
    ctx.globalAlpha = 0.7;
    ctx.fillRect(x * cellW, y * cellH, cellW, cellH);
    ctx.globalAlpha = 1.0;
  }

  // --- events --------------------------------------------------------------

  function postEvent(payload) {
    fetch("/xnano/event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  var NAMED = {
    " ": "space", "Escape": "esc", "Enter": "enter",
    "Backspace": "backspace", "Tab": "tab", "Delete": "delete",
    "ArrowUp": "up", "ArrowDown": "down",
    "ArrowLeft": "left", "ArrowRight": "right",
    "Home": "home", "End": "end",
    "PageUp": "pageup", "PageDown": "pagedown", "Insert": "insert",
  };

  document.addEventListener("keydown", function (event) {
    var named = NAMED[event.key];
    var key, char = null;
    if (named) {
      key = named;
    } else if (event.key.length === 1) {
      key = event.key.toLowerCase();
      char = event.key;               // preserve case / symbol for typing
    } else {
      return;                          // ignore modifier-only / dead keys
    }
    var mods = [];
    if (event.ctrlKey) { mods.push("ctrl"); }
    if (event.altKey) { mods.push("alt"); }
    if (event.shiftKey) { mods.push("shift"); }
    event.preventDefault();
    postEvent({ type: "key", binding: mods.concat([key]).join("+"), char: char });
  });

  function cellFromMouse(event) {
    return [
      Math.floor(event.clientX / cellW),
      Math.floor(event.clientY / cellH),
    ];
  }

  canvas.addEventListener("mousedown", function (event) {
    var pos = cellFromMouse(event);
    var button = ["left", "middle", "right"][event.button] || "left";
    postEvent({ type: "mouse", kind: "press", button: button, x: pos[0], y: pos[1] });
  });

  canvas.addEventListener("mouseup", function (event) {
    var pos = cellFromMouse(event);
    var button = ["left", "middle", "right"][event.button] || "left";
    postEvent({ type: "mouse", kind: "release", button: button, x: pos[0], y: pos[1] });
  });

  var resizeTimer = null;
  function sendResize() {
    var size = gridSize();
    postEvent({ type: "resize", cols: size[0], rows: size[1] });
  }
  window.addEventListener("resize", function () {
    resizeCanvas();
    if (resizeTimer) { clearTimeout(resizeTimer); }
    resizeTimer = setTimeout(sendResize, 120);
  });

  // --- boot ----------------------------------------------------------------

  measureCell();
  resizeCanvas();
  var initial = gridSize();
  var source = new EventSource("/xnano/stream?cols=" + initial[0] + "&rows=" + initial[1]);
  source.onmessage = function (event) {
    applyFrame(JSON.parse(event.data));
  };
})();
