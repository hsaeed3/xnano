/*
 * The hairline box around the page title, drawn along the title's lines.
 *
 * A border around a wrapped heading keeps the full measure on every line. This draws the box
 * as one SVG path instead, measured from the letters rather than from the line boxes: the
 * heading's padding is left above the first line's capitals, below the last baseline, before
 * the text and after each line's end, and neighbouring lines meet halfway between one line's
 * descenders and the next line's ascenders, so the step never touches a letter. A heading that
 * wraps gets a box that steps in around a shorter last line. The colour and width come from
 * `.xn-heading-box` in content.css.
 */
(function () {
    "use strict";

    const SVG = "http://www.w3.org/2000/svg";
    const HEADINGS = ".xn-masthead h1";
    const canvas = document.createElement("canvas").getContext("2d");
    const observer = new ResizeObserver((entries) => {
        for (const entry of entries) draw(entry.target);
    });

    // The ascent and descent of an element's font, and how far its capitals, ascenders and
    // descenders reach from the baseline, in pixels.
    function fontMetrics(element) {
        const style = getComputedStyle(element);
        canvas.font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
        const capital = canvas.measureText("H");
        return {
            ascent: capital.fontBoundingBoxAscent,
            descent: capital.fontBoundingBoxDescent,
            capital: capital.actualBoundingBoxAscent,
            ascender: canvas.measureText("bdfhklt").actualBoundingBoxAscent,
            descender: canvas.measureText("gjpqy").actualBoundingBoxDescent,
        };
    }

    // A heading's text as one entry per line, top to bottom: where it starts and ends, and its
    // baseline.
    function textLines(heading) {
        const lines = [];
        const walker = document.createTreeWalker(heading, NodeFilter.SHOW_TEXT, {
            acceptNode: (node) =>
                node.parentElement.closest(".headerlink, .xn-heading-box")
                    ? NodeFilter.FILTER_REJECT
                    : NodeFilter.FILTER_ACCEPT,
        });
        const range = document.createRange();
        for (let node = walker.nextNode(); node; node = walker.nextNode()) {
            const font = fontMetrics(node.parentElement);
            range.selectNodeContents(node);
            for (const rect of range.getClientRects()) {
                if (rect.width === 0) continue;
                const baseline = rect.top + (rect.height * font.ascent) / (font.ascent + font.descent);
                const line = lines.find((line) => Math.abs(line.baseline - baseline) < 2);
                if (line) {
                    line.left = Math.min(line.left, rect.left);
                    line.right = Math.max(line.right, rect.right);
                } else {
                    lines.push({ left: rect.left, right: rect.right, baseline });
                }
            }
        }
        return lines.sort((first, second) => first.baseline - second.baseline);
    }

    function draw(heading) {
        let box = heading.querySelector(":scope > .xn-heading-box");
        if (!box) {
            box = document.createElementNS(SVG, "svg");
            box.setAttribute("class", "xn-heading-box");
            box.setAttribute("aria-hidden", "true");
            box.append(document.createElementNS(SVG, "path"));
            heading.append(box);
        }
        const lines = textLines(heading);
        if (!lines.length) return;
        // The first letter's ink starts its side bearing after the text's edge; the title hangs
        // that much further into the margin (see `--xn-title-bearing` in content.css).
        const style = getComputedStyle(heading);
        canvas.font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
        const bearing = -canvas.measureText(heading.textContent.trim().charAt(0)).actualBoundingBoxLeft;
        heading.style.setProperty("--xn-title-bearing", `${Math.max(0, bearing)}px`);
        const origin = heading.getBoundingClientRect();
        const padding = parseFloat(getComputedStyle(heading).paddingLeft);
        const font = fontMetrics(heading);
        // Whole pixels plus a half keep a one-pixel hairline crisp.
        const column = (value) => Math.round(value - origin.left) + 0.5;
        const row = (value) => Math.round(value - origin.top) + 0.5;
        const left = column(Math.min(...lines.map((line) => line.left)) - padding);
        let path = `M${left} ${row(lines[0].baseline - font.capital - padding)}`;
        lines.forEach((line, index) => {
            const next = lines[index + 1];
            const end = next
                ? (line.baseline + font.descender + next.baseline - font.ascender) / 2
                : line.baseline + padding;
            path += ` H${column(line.right + padding) - 1} V${row(end)}`;
        });
        box.firstChild.setAttribute("d", `${path} H${left} Z`);
    }

    function attach() {
        observer.disconnect();
        const headings = document.querySelectorAll(HEADINGS);
        for (const heading of headings) observer.observe(heading);
        // Web fonts change the text's width without always changing a heading's size.
        document.fonts.ready.then(() => headings.forEach(draw));
    }

    // With instant navigation, `document$` emits after every page change.
    if (typeof document$ !== "undefined") {
        document$.subscribe(attach);
    } else {
        document.addEventListener("DOMContentLoaded", attach);
    }
})();
