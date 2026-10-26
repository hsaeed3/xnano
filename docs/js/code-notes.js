// Code comments: mark lines of a code block with `# >> [name]`, and explain them in a
// `<comments>` element written right after the block.
//
//     ```python
//     picture = xnano.load_image('dusk.png', width='100%')  # >> [image]
//     with xnano.open() as terminal:  # >> [terminal]
//         terminal.screen.write(picture)  # >> [terminal]
//     ```
//
//     <comments>
//     <definition term="load_image" kind="function">Reads PNG, JPEG, GIF, WebP and XNI files.</definition>
//
//     <tag name="image" color="pink">
//     Loads the picture at the full width of the screen.
//     </tag>
//
//     <tag name="terminal" color="#5a85ff">
//     Opens a live terminal and draws the picture on it. Any **markdown** works here.
//
//     <definition term="write" kind="method">Places the picture on this screen.</definition>
//     </tag>
//     </comments>
//
// - `# >> [name]` at the end of a line marks it for the `<tag>` of that name. Every line with
//   the name belongs to one note, written once, and the lines light up together.
// - `<tag name="...">` holds the note, in any markdown.
// - `<definition term="...">` defines a piece of code wherever it appears in the block.
//   Written inside a `<tag>`, it defines the term only on that tag's lines, in place of a
//   definition of the same term written for the whole block.
// - `kind="..."` on a definition says what the term is, and sets how it is underlined:
//   function, method, class, type, module, package, parameter, attribute, property,
//   constant, value, variable, keyword, decorator or exception.
// - `color="..."` on a tag or a definition colors its lines or its term: blue, pink, purple,
//   amber, green or red from the site's palette, any other CSS color name, or a hex code
//   such as #5a85ff. A definition inside a colored tag takes the tag's color unless it has
//   its own.
//
// Nothing is shown until it is asked for. While the pointer (or the keyboard focus) is on a
// marked line, a tooltip under it shows the note, with its tag's definitions; on a defined
// term, it shows the term's definition, and every place the term appears is underlined. The
// tooltip closes as soon as the code is left. On a phone, a tap pins it open and another tap,
// or a tap elsewhere, closes it. The markers are removed, so copying a block copies
// clean code. The markdown extension in scripts/docs_markdown keeps these elements whole.
// Works on highlighted blocks and on any element marked `data-xn-code` whose lines are
// wrapped in `span[id^="__span-"]`.
(function () {
    "use strict";

    const COMMENTS = ".c, .c1, .ch, .cm, .cs";
    const MARKER = /^\s*(?:#|\/\/|--|;)\s*>>\s*\[([^\]]+)\]\s*$/;
    const KINDS = [
        "function",
        "method",
        "class",
        "type",
        "module",
        "package",
        "parameter",
        "attribute",
        "property",
        "constant",
        "value",
        "variable",
        "keyword",
        "decorator",
        "exception",
    ];
    const PALETTE = ["blue", "pink", "purple", "amber", "green", "red"];
    const WORD = /\w/;

    let sequence = 0;

    function resolveColor(value, owner) {
        if (value === null) return null;
        const color = value.trim();
        if (PALETTE.includes(color.toLowerCase())) return `var(--xn-color-${color.toLowerCase()})`;
        if (color && CSS.supports("color", color)) return color;
        console.warn(
            `${owner} has color="${value}", which is not a color. Use ${PALETTE.join(", ")}, ` +
                "another CSS color name, or a hex code such as #5a85ff.",
        );
        return null;
    }

    function childrenNamed(element, name) {
        return [...element.children].filter((child) => child.localName === name);
    }

    function readDefinition(element, place) {
        const term = (element.getAttribute("term") || "").trim();
        if (!term) {
            console.warn(`A <definition> ${place} has no term="...". Add the piece of code it defines.`);
            return null;
        }
        const kind = (element.getAttribute("kind") || "").trim().toLowerCase();
        if (kind && !KINDS.includes(kind)) {
            console.warn(`<definition term="${term}"> has kind="${kind}". Use one of: ${KINDS.join(", ")}.`);
        }
        return {
            id: `xn-term-${++sequence}`,
            term,
            kind: KINDS.includes(kind) ? kind : null,
            color: resolveColor(element.getAttribute("color"), `<definition term="${term}">`),
            content: [...element.childNodes],
        };
    }

    // The block's definitions, and its tags by name with their own definitions.
    function readComments(comments) {
        const definitions = childrenNamed(comments, "definition")
            .map((element) => readDefinition(element, "in <comments>"))
            .filter(Boolean);
        const tags = new Map();
        childrenNamed(comments, "tag").forEach((element) => {
            const name = (element.getAttribute("name") || "").trim();
            if (!name) {
                console.warn('A <tag> has no name="...". Give it the name its lines use in # >> [name].');
                return;
            }
            const color = resolveColor(element.getAttribute("color"), `<tag name="${name}">`);
            const own = childrenNamed(element, "definition")
                .map((definition) => readDefinition(definition, `in <tag name="${name}">`))
                .filter(Boolean);
            own.forEach((definition) => (definition.color = definition.color || color));
            tags.set(name, {
                name,
                color,
                definitions: own,
                content: [...element.childNodes].filter((node) => node.localName !== "definition"),
            });
        });
        return { definitions, tags };
    }

    function findComments(block, pre) {
        for (const candidate of [pre.nextElementSibling, block.nextElementSibling]) {
            if (candidate && candidate.localName === "comments") return candidate;
        }
        return null;
    }

    function removeComment(comment) {
        const before = comment.previousSibling;
        if (before && before.nodeType === Node.TEXT_NODE) {
            before.textContent = before.textContent.replace(/[ \t]+$/, "");
        } else if (before && before.textContent.trim() === "") {
            before.remove();
        }
        comment.remove();
    }

    function lineNumber(line, fallback) {
        const match = line.id.match(/(\d+)$/);
        return match ? Number(match[1]) : fallback;
    }

    // The marked lines of a block, grouped by name in reading order: [{ name, lines }].
    function collectMarks(lines) {
        const marks = new Map();
        lines.forEach((line, index) => {
            const comment = [...line.querySelectorAll(COMMENTS)].find((candidate) =>
                MARKER.test(candidate.textContent),
            );
            if (!comment) return;
            const name = comment.textContent.match(MARKER)[1].trim();
            removeComment(comment);
            if (!marks.has(name)) marks.set(name, { name, lines: [] });
            marks.get(name).lines.push({ element: line, number: lineNumber(line, index + 1) });
        });
        return [...marks.values()];
    }

    function textNodes(element) {
        const nodes = [];
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) nodes.push(walker.currentNode);
        return nodes;
    }

    // Where a term appears in a text, as a whole word when it starts or ends with one.
    function occurrences(text, term) {
        const found = [];
        const checksStart = WORD.test(term[0]);
        const checksEnd = WORD.test(term[term.length - 1]);
        for (let start = text.indexOf(term); start >= 0; start = text.indexOf(term, start + 1)) {
            const before = text[start - 1];
            const after = text[start + term.length];
            if (checksStart && before && WORD.test(before)) continue;
            if (checksEnd && after && WORD.test(after)) continue;
            found.push(start);
        }
        return found;
    }

    // Wrap the characters from start to end of a line's text, which may cross token spans,
    // in `.xn-term` spans for one definition.
    function wrap(line, start, end, definition) {
        let offset = 0;
        const segments = [];
        for (const node of textNodes(line)) {
            const length = node.textContent.length;
            const from = Math.max(start, offset);
            const to = Math.min(end, offset + length);
            if (from < to) segments.push({ node, from: from - offset, to: to - offset });
            offset += length;
            if (offset >= end) break;
        }
        segments.forEach(({ node, from, to }, index) => {
            const piece = from > 0 ? node.splitText(from) : node;
            if (to - from < piece.textContent.length) piece.splitText(to - from);
            const span = document.createElement("span");
            span.className = "xn-term";
            span.dataset.xnTerm = definition.id;
            if (index === 0) span.tabIndex = 0;
            if (definition.kind) span.dataset.kind = definition.kind;
            if (definition.color) span.style.setProperty("--xn-term-color", definition.color);
            piece.replaceWith(span);
            span.appendChild(piece);
        });
    }

    // Mark every appearance of a defined term on a line, longer terms first.
    function defineTerms(line, definitions) {
        const text = textNodes(line)
            .map((node) => node.textContent)
            .join("");
        const claimed = [];
        [...definitions]
            .sort((first, second) => second.term.length - first.term.length)
            .forEach((definition) => {
                occurrences(text, definition.term).forEach((start) => {
                    const end = start + definition.term.length;
                    if (claimed.some((range) => start < range.end && end > range.start)) return;
                    claimed.push({ start, end, definition });
                });
            });
        claimed.forEach(({ start, end, definition }) => wrap(line, start, end, definition));
    }

    // Mark each code span in a note that names a defined term, so it lights up with the term.
    function linkMentions(container, definitions) {
        const byTerm = new Map(definitions.map((definition) => [definition.term, definition]));
        container.querySelectorAll("code").forEach((code) => {
            if (code.closest("pre, dt")) return;
            const definition = byTerm.get(code.textContent.trim());
            if (!definition) return;
            code.classList.add("xn-mention");
            code.dataset.xnTerm = definition.id;
            if (definition.color) code.style.setProperty("--xn-term-color", definition.color);
        });
    }

    // Definitions as a list: each term in code and its kind in a word, then what it is.
    function buildDefinitions(definitions) {
        const list = document.createElement("dl");
        list.className = "xn-definitions";
        definitions.forEach((definition) => {
            const entry = document.createElement("div");
            entry.className = "xn-definition";
            entry.dataset.xnTerm = definition.id;
            if (definition.color) entry.style.setProperty("--xn-term-color", definition.color);
            const term = document.createElement("dt");
            const code = document.createElement("code");
            code.textContent = definition.term;
            term.appendChild(code);
            if (definition.kind) {
                const kind = document.createElement("span");
                kind.className = "xn-definition__kind";
                kind.textContent = definition.kind;
                term.append(" ", kind);
            }
            const description = document.createElement("dd");
            description.append(...definition.content);
            entry.append(term, description);
            list.appendChild(entry);
        });
        return list;
    }

    // The box around a line's code, from its first to its last visible character.
    function codeExtent(line) {
        const nodes = textNodes(line).filter((node) => node.textContent.trim());
        if (!nodes.length) return null;
        const first = nodes[0];
        const last = nodes[nodes.length - 1];
        const range = document.createRange();
        range.setStart(first, first.textContent.search(/\S/));
        range.setEnd(last, last.textContent.replace(/\s+$/, "").length);
        return range.getBoundingClientRect();
    }

    function enhance(block) {
        if (block.dataset.xnNotes) return;
        const code = block.querySelector("pre > code");
        if (!code) return;
        const pre = code.parentElement;
        const comments = findComments(block, pre);
        const lines = [...code.querySelectorAll('span[id^="__span-"]')];
        const marks = collectMarks(lines);
        block.dataset.xnNotes = String(marks.length);
        if (!comments) {
            marks.forEach((mark) =>
                console.warn(`Lines end with # >> [${mark.name}], but no <comments> follows their code block.`),
            );
            return;
        }

        const { definitions, tags } = readComments(comments);
        const notes = marks.filter((mark) => {
            if (tags.has(mark.name)) return true;
            console.warn(`Lines end with # >> [${mark.name}], but their <comments> has no <tag name="${mark.name}">.`);
            return false;
        });
        tags.forEach((tag, name) => {
            if (!marks.some((mark) => mark.name === name)) {
                console.warn(`<tag name="${name}"> is not used: no line of its code block ends with # >> [${name}].`);
            }
        });

        // Terms: a tag's own definitions on its lines, the block's everywhere else.
        const noteOfLine = new Map();
        notes.forEach((note) => note.lines.forEach(({ element }) => noteOfLine.set(element, note)));
        lines.forEach((line) => {
            const note = noteOfLine.get(line);
            const own = note ? tags.get(note.name).definitions : [];
            const ownTerms = new Set(own.map((definition) => definition.term));
            defineTerms(line, [...own, ...definitions.filter((definition) => !ownTerms.has(definition.term))]);
        });

        block.classList.add("xn-noted");
        const layer = document.createElement("div");
        layer.className = "xn-notes";
        block.appendChild(layer);
        const tooltip = document.createElement("div");
        tooltip.className = "xn-tooltip";
        tooltip.id = `xn-tooltip-${++sequence}`;
        tooltip.setAttribute("role", "tooltip");

        // What each note shows, built once: its text, then its own definitions. Each marked
        // line gets a hairline in the margin and a quiet wash behind its code while open.
        const entries = notes.map((note, index) => {
            const tag = tags.get(note.name);
            const content = document.createElement("div");
            content.className = "xn-tooltip__note";
            content.append(...tag.content);
            if (tag.definitions.length) content.appendChild(buildDefinitions(tag.definitions));
            linkMentions(content, [...tag.definitions, ...definitions]);
            const marked = note.lines.map(({ element }) => {
                element.dataset.xnNote = String(index);
                element.tabIndex = 0;
                const rule = document.createElement("div");
                rule.className = "xn-note__rule";
                const wash = document.createElement("div");
                wash.className = "xn-note__wash";
                [rule, wash].forEach((part) => {
                    if (tag.color) part.style.setProperty("--xn-note-color", tag.color);
                    layer.appendChild(part);
                });
                return { line: element, rule, wash };
            });
            return { note, tag, content, marked };
        });
        const blockDefinitions = new Map(
            definitions.map((definition) => {
                const list = buildDefinitions([definition]);
                linkMentions(list, definitions);
                return [definition.id, list];
            }),
        );
        comments.remove();
        block.appendChild(tooltip);

        const highlight = (term) => {
            block.querySelectorAll("[data-xn-term].is-active").forEach((element) =>
                element.classList.remove("is-active"),
            );
            if (!term) return;
            block.querySelectorAll(`[data-xn-term="${term}"]`).forEach((element) =>
                element.classList.add("is-active"),
            );
        };

        // The tooltip sits just below what it explains, or just above it when the screen has no
        // room below, and stays inside the block's width.
        // A line's note opens below the last line of its run (above the first, when it opens
        // upward), so it never covers the lines it explains.
        const anchorBox = (anchor) => {
            if (anchor.classList.contains("xn-term")) return anchor.getBoundingClientRect();
            const start = codeExtent(anchor) || anchor.getBoundingClientRect();
            const entry = entries[Number(anchor.dataset.xnNote)];
            if (!entry) return start;
            const numbers = entry.note.lines.map(({ number }) => number);
            const index = entry.note.lines.findIndex(({ element }) => element === anchor);
            let first = index;
            let last = index;
            while (first > 0 && numbers[first - 1] === numbers[first] - 1) first -= 1;
            while (last < numbers.length - 1 && numbers[last + 1] === numbers[last] + 1) last += 1;
            const top = entry.note.lines[first].element.getBoundingClientRect().top;
            const bottom = entry.note.lines[last].element.getBoundingClientRect().bottom;
            return { left: start.left, width: start.width, top, bottom };
        };

        const placeTooltip = (anchor) => {
            const origin = block.getBoundingClientRect();
            const target = anchorBox(anchor);
            tooltip.style.maxWidth = `${Math.max(200, Math.min(420, origin.width - 24))}px`;
            const width = tooltip.offsetWidth;
            const height = tooltip.offsetHeight;
            const left = Math.max(12, Math.min(target.left - origin.left, origin.width - width - 12));
            const isAbove = target.bottom + 8 + height > window.innerHeight && target.top - 8 - height > 0;
            tooltip.style.left = `${left}px`;
            tooltip.style.top = `${isAbove ? target.top - origin.top - 8 - height : target.bottom - origin.top + 8}px`;
        };

        // What is shown: a note (by index), a term (by id) and the code it belongs to, or null.
        // The tooltip only describes the code under the pointer or the focus: it never takes the
        // pointer itself, and it closes as soon as that code is left.
        let shown = null;
        let pinned = null;

        const show = (state) => {
            const isSame =
                state && shown && state.note === shown.note && state.term === shown.term && state.anchor === shown.anchor;
            if (isSame || (!state && !shown)) return;
            if (shown) shown.anchor.removeAttribute("aria-describedby");
            shown = state;
            entries.forEach((entry, index) => {
                const isOpen = state !== null && state.note === index;
                entry.marked.forEach(({ line, rule, wash }) => {
                    rule.classList.toggle("is-active", isOpen);
                    wash.classList.toggle("is-active", isOpen);
                    line.classList.toggle("xn-note-open", isOpen);
                });
            });
            highlight(state ? state.term : null);
            const parts = [];
            if (state && state.note >= 0) parts.push(entries[state.note].content);
            const own = state && state.note >= 0 ? entries[state.note].tag.definitions : [];
            if (state && state.term && blockDefinitions.has(state.term) && !own.some((definition) => definition.id === state.term)) {
                parts.push(blockDefinitions.get(state.term));
            }
            if (!parts.length) {
                tooltip.classList.remove("is-open");
                return;
            }
            tooltip.replaceChildren(...parts);
            placeTooltip(state.anchor);
            state.anchor.setAttribute("aria-describedby", tooltip.id);
            tooltip.classList.add("is-open");
        };

        const stateAt = (target) => {
            const line = target.closest("[data-xn-note]");
            const term = target.closest(".xn-term");
            if (!line && !term) return null;
            const note = line ? Number(line.dataset.xnNote) : -1;
            return { note, term: term ? term.dataset.xnTerm : null, anchor: term || line };
        };

        const isTouch = () => window.matchMedia("(hover: none)").matches;

        code.addEventListener("mouseover", (event) => {
            if (!isTouch()) show(stateAt(event.target) || pinned);
        });
        code.addEventListener("mouseleave", () => show(pinned));
        code.addEventListener("focusin", (event) => show(stateAt(event.target)));
        code.addEventListener("focusout", () => show(pinned));
        code.addEventListener("click", (event) => {
            if (!isTouch()) return;
            const state = stateAt(event.target);
            const isSame = state && pinned && state.note === pinned.note && state.term === pinned.term;
            pinned = isSame ? null : state;
            show(pinned);
        });
        document.addEventListener("click", (event) => {
            if (pinned && !block.contains(event.target)) {
                pinned = null;
                show(null);
            }
        });
        block.addEventListener("keydown", (event) => {
            if (event.key !== "Escape") return;
            pinned = null;
            show(null);
        });

        // A wash covers its line's code where the code is visible, never past the block.
        const place = () => {
            const origin = block.getBoundingClientRect();
            const view = code.getBoundingClientRect();
            entries.forEach((entry) => {
                entry.marked.forEach(({ line, rule, wash }) => {
                    const box = line.getBoundingClientRect();
                    rule.style.top = `${box.top - origin.top}px`;
                    rule.style.height = `${box.height}px`;
                    const extent = codeExtent(line);
                    const left = extent ? Math.max(extent.left - 3, view.left) : 0;
                    const right = extent ? Math.min(extent.right + 3, view.right) : 0;
                    wash.style.display = right > left ? "" : "none";
                    if (right <= left) return;
                    wash.style.left = `${left - origin.left}px`;
                    wash.style.top = `${box.top - origin.top}px`;
                    wash.style.width = `${right - left}px`;
                    wash.style.height = `${box.height}px`;
                });
            });
            if (shown && tooltip.classList.contains("is-open")) placeTooltip(shown.anchor);
        };

        code.addEventListener("scroll", place, { passive: true });
        if (typeof ResizeObserver !== "undefined") new ResizeObserver(place).observe(block);
        if (document.fonts && document.fonts.ready) document.fonts.ready.then(place);
        place();
    }

    function enhanceAll() {
        document.querySelectorAll(".highlight, [data-xn-code]").forEach(enhance);
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
