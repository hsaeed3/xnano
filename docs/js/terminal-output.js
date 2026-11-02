// Terminal output: the output of a runnable (```pyodide) code block shows the colors and
// styles that xnano prints, as `canvas.screen.render(format='ansi')` gives them.
//
// - Each output panel is watched, and whenever its text holds ANSI escape codes, they are
//   turned into styled text: the 16 named colors use the --xn-ansi-* tokens, so they follow
//   the site's color scheme, and 256-color and red, green, blue colors are drawn as written.
//   Bold, dim, italic, underline, reverse video and crossed out text are kept; any other
//   escape sequence is dropped.
// - A block inside an element with `data-xn-preview` shows the saved output that attribute
//   names until it is run, so the homepage's first example has its result on screen without
//   loading Python. Running the block replaces it.
(function () {
    "use strict";

    const ESCAPE = /\x1b\[([0-9;]*)m|\x1b\[[0-9;?]*[A-Za-z]|\x1b[^[]/g;
    const COLOR_NAMES = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"];
    const CUBE_LEVELS = [0, 95, 135, 175, 215, 255];
    const WATCHED = { childList: true, characterData: true, subtree: true };

    function namedColor(number) {
        const prefix = number >= 8 ? "bright-" : "";
        return `var(--xn-ansi-${prefix}${COLOR_NAMES[number % 8]})`;
    }

    // The xterm palette of 256 colors: the 16 named colors, a 6×6×6 cube, then 24 grays.
    function indexedColor(number) {
        if (number < 16) return namedColor(number);
        if (number < 232) {
            const cube = number - 16;
            const red = CUBE_LEVELS[Math.floor(cube / 36)];
            const green = CUBE_LEVELS[Math.floor(cube / 6) % 6];
            const blue = CUBE_LEVELS[cube % 6];
            return `rgb(${red}, ${green}, ${blue})`;
        }
        const gray = 8 + (number - 232) * 10;
        return `rgb(${gray}, ${gray}, ${gray})`;
    }

    function plainStyle() {
        return {
            foreground: null,
            background: null,
            isBold: false,
            isDim: false,
            isItalic: false,
            isUnderlined: false,
            isReversed: false,
            isCrossedOut: false,
        };
    }

    // Apply the parameters of one `ESC [ ... m` sequence to the current style.
    function applyParameters(style, parameters) {
        const codes = parameters === "" ? [0] : parameters.split(";").map(Number);
        for (let index = 0; index < codes.length; index++) {
            const code = codes[index];
            if (code === 0) Object.assign(style, plainStyle());
            else if (code === 1) style.isBold = true;
            else if (code === 2) style.isDim = true;
            else if (code === 3) style.isItalic = true;
            else if (code === 4) style.isUnderlined = true;
            else if (code === 7) style.isReversed = true;
            else if (code === 9) style.isCrossedOut = true;
            else if (code === 22) style.isBold = style.isDim = false;
            else if (code === 23) style.isItalic = false;
            else if (code === 24) style.isUnderlined = false;
            else if (code === 27) style.isReversed = false;
            else if (code === 29) style.isCrossedOut = false;
            else if (code >= 30 && code <= 37) style.foreground = namedColor(code - 30);
            else if (code >= 90 && code <= 97) style.foreground = namedColor(code - 82);
            else if (code === 39) style.foreground = null;
            else if (code >= 40 && code <= 47) style.background = namedColor(code - 40);
            else if (code >= 100 && code <= 107) style.background = namedColor(code - 92);
            else if (code === 49) style.background = null;
            else if (code === 38 || code === 48) {
                let color = null;
                if (codes[index + 1] === 5) {
                    color = indexedColor(codes[index + 2]);
                    index += 2;
                } else if (codes[index + 1] === 2) {
                    color = `rgb(${codes[index + 2]}, ${codes[index + 3]}, ${codes[index + 4]})`;
                    index += 4;
                }
                if (code === 38) style.foreground = color;
                else style.background = color;
            }
        }
    }

    function isPlain(style) {
        const plain = plainStyle();
        return Object.keys(plain).every((key) => style[key] === plain[key]);
    }

    function styledText(style, text) {
        if (isPlain(style)) return document.createTextNode(text);
        const span = document.createElement("span");
        span.textContent = text;
        let foreground = style.foreground;
        let background = style.background;
        if (style.isReversed) {
            foreground = style.background || "var(--xn-terminal-background)";
            background = style.foreground || "var(--xn-terminal-foreground)";
        }
        if (foreground) span.style.color = foreground;
        if (background) span.style.backgroundColor = background;
        if (style.isBold) span.style.fontWeight = "600";
        if (style.isDim) span.style.opacity = "0.6";
        if (style.isItalic) span.style.fontStyle = "italic";
        const lines = [];
        if (style.isUnderlined) lines.push("underline");
        if (style.isCrossedOut) lines.push("line-through");
        if (lines.length > 0) span.style.textDecoration = lines.join(" ");
        return span;
    }

    function render(output, text) {
        const fragment = document.createDocumentFragment();
        const style = plainStyle();
        let position = 0;
        for (const match of text.matchAll(ESCAPE)) {
            if (match.index > position) {
                fragment.append(styledText(style, text.slice(position, match.index)));
            }
            if (match[1] !== undefined) applyParameters(style, match[1]);
            position = match.index + match[0].length;
        }
        if (position < text.length) fragment.append(styledText(style, text.slice(position)));
        output.replaceChildren(fragment);
    }

    function watch(output) {
        if (output.dataset.xnTerminalOutput) return;
        output.dataset.xnTerminalOutput = "watched";
        const observer = new MutationObserver(update);
        function update() {
            const text = output.textContent;
            if (!text.includes("\x1b")) return;
            observer.disconnect();
            render(output, text);
            observer.observe(output, WATCHED);
        }
        observer.observe(output, WATCHED);
        update();
    }

    function showPreview(container) {
        const output = container.querySelector(".pyodide-output");
        if (!output || output.textContent.trim() !== "") return;
        fetch(container.dataset.xnPreview)
            .then((response) => (response.ok ? response.text() : ""))
            .then((text) => {
                // A run that started while the preview loaded keeps its own output.
                if (text && output.textContent.trim() === "") output.textContent = text;
            })
            .catch(() => {
                // Without the preview the panel stays empty until the block is run.
            });
    }

    // markdown-exec names the session of every editor, which only matters to a page whose
    // blocks share one, so the default session's editor is just called the editor.
    function nameEditor(label) {
        if (label.textContent.trim() === "Editor (session: default)") label.textContent = "Editor";
    }

    function enhanceAll() {
        document.querySelectorAll(".pyodide-editor-bar > .pyodide-bar-item:first-child").forEach(nameEditor);
        document.querySelectorAll(".pyodide-output").forEach(watch);
        document.querySelectorAll("[data-xn-preview]").forEach(showPreview);
    }

    // With instant navigation, `document$` emits after every page change.
    if (typeof document$ !== "undefined") {
        document$.subscribe(enhanceAll);
    } else if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", enhanceAll);
    } else {
        enhanceAll();
    }
})();
