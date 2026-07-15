function setupTermynal() {
    document.querySelectorAll(".use-termynal").forEach(node => {
        node.style.display = "block";
        new Termynal(node, {
            lineDelay: 500
        });
    });
    const progressLiteralStart = "---> 100%";
    const promptLiteralStart = "$ ";
    const customPromptLiteralStart = "# ";
    const termynalActivateClass = "termy";
    let termynals = [];

    function createTermynals() {
        document
            .querySelectorAll(`.${termynalActivateClass} .highlight code`)
            .forEach(node => {
                const text = node.textContent;
                const lines = text.split("\n");
                const useLines = [];
                let buffer = [];
                function saveBuffer() {
                    if (buffer.length) {
                        let isBlankSpace = true;
                        buffer.forEach(line => {
                            if (line) {
                                isBlankSpace = false;
                            }
                        });
                        dataValue = {};
                        if (isBlankSpace) {
                            dataValue["delay"] = 0;
                        }
                        if (buffer[buffer.length - 1] === "") {
                            // A last single <br> won't have effect
                            // so put an additional one
                            buffer.push("");
                        }
                        const bufferValue = buffer.join("<br>");
                        dataValue["value"] = bufferValue;
                        useLines.push(dataValue);
                        buffer = [];
                    }
                }
                for (let line of lines) {
                    if (line === progressLiteralStart) {
                        saveBuffer();
                        useLines.push({
                            type: "progress"
                        });
                    } else if (line.startsWith(promptLiteralStart)) {
                        saveBuffer();
                        const value = line.replace(promptLiteralStart, "").trimEnd();
                        useLines.push({
                            type: "input",
                            value: value
                        });
                    } else if (line.startsWith("// ")) {
                        saveBuffer();
                        const value = "💬 " + line.replace("// ", "").trimEnd();
                        useLines.push({
                            value: value,
                            class: "termynal-comment",
                            delay: 0
                        });
                    } else if (line.startsWith(customPromptLiteralStart)) {
                        saveBuffer();
                        const promptStart = line.indexOf(promptLiteralStart);
                        if (promptStart === -1) {
                            console.error("Custom prompt found but no end delimiter", line)
                        }
                        const prompt = line.slice(0, promptStart).replace(customPromptLiteralStart, "")
                        let value = line.slice(promptStart + promptLiteralStart.length);
                        useLines.push({
                            type: "input",
                            value: value,
                            prompt: prompt
                        });
                    } else {
                        buffer.push(line);
                    }
                }
                saveBuffer();
                const inputCommands = useLines.filter(line => line.type === "input").map(line => line.value).join("\n");
                node.textContent = inputCommands;
                const div = document.createElement("div");
                node.style.display = "none";
                node.after(div);
                const termynal = new Termynal(div, {
                    lineData: useLines,
                    noInit: true,
                    lineDelay: 500
                });
                termynals.push(termynal);
            });
    }

    function loadVisibleTermynals() {
        termynals = termynals.filter(termynal => {
            if (termynal.container.getBoundingClientRect().top - innerHeight <= 0) {
                termynal.init();
                return false;
            }
            return true;
        });
    }
    window.addEventListener("scroll", loadVisibleTermynals);
    createTermynals();
    loadVisibleTermynals();
}

function openLinksInNewTab() {
    const siteUrl = document.querySelector("link[rel='canonical']")?.href
        || window.location.origin;
    const siteOrigin = new URL(siteUrl).origin;
    document.querySelectorAll(".md-content a[href]").forEach(a => {
        if (a.getAttribute("target") === "_self") return;
        const href = a.getAttribute("href");
        if (!href) return;
        try {
            const url = new URL(href, window.location.href);
            // Skip same-page anchor links (only the hash differs)
            if (url.origin === window.location.origin
                && url.pathname === window.location.pathname
                && url.search === window.location.search) return;
            if (!a.hasAttribute("target")) {
                a.setAttribute("target", "_blank");
                a.setAttribute("rel", "noopener");
            }
            if (url.origin !== siteOrigin) {
                a.dataset.externalLink = "";
            } else {
                a.dataset.internalLink = "";
            }
        } catch (_) {}
    });
}

// Picks two neighboring colors from a restrained pastel palette once per
// page load and hands them to nav.css as CSS vars. This intentionally stays
// independent from the brighter hero palette.
// This is a single synchronous pick — no animation loop, no per-frame cost.
function setupNavAccent() {
    const palettes = {
        default: [
            [100, 117, 160], // dusty cornflower
            [111, 133, 174], // powder blue
            [98, 137, 158],  // blue mist
            [121, 125, 166], // muted periwinkle
        ],
        slate: [
            [178, 192, 223], // moonlit blue
            [184, 202, 228], // powder blue
            [165, 202, 210], // blue mist
            [190, 194, 225], // pale periwinkle
        ],
        "serif-default": [
            [189, 91, 88],
            [217, 111, 85],
            [198, 83, 101],
            [231, 137, 92],
        ],
        "serif-slate": [
            [239, 142, 115],
            [244, 174, 121],
            [222, 118, 130],
            [236, 156, 104],
        ],
        "modern-default": [
            [82, 121, 120],
            [103, 146, 145],
            [75, 133, 128],
            [110, 151, 145],
        ],
        "modern-slate": [
            [155, 199, 195],
            [182, 217, 213],
            [137, 189, 184],
            [168, 207, 202],
        ],
    };

    function pickColors() {
        const scheme = document.body.getAttribute("data-md-color-scheme");
        const style = document.documentElement.dataset.xnanoStyle || "mono";
        const paletteKey = style === "mono" ? scheme : `${style}-${scheme}`;
        const palette = palettes[paletteKey] || palettes.slate;
        const index = Math.floor(Math.random() * palette.length);
        const base = palette[index];
        const companion = palette[(index + 1) % palette.length];
        const toRgb = ([r, g, b]) => `rgb(${r}, ${g}, ${b})`;
        document.documentElement.style.setProperty("--xnano-nav-c1", toRgb(base));
        document.documentElement.style.setProperty("--xnano-nav-c2", toRgb(companion));
    }

    pickColors();
    new MutationObserver(pickColors).observe(document.body, {
        attributes: true,
        attributeFilter: ["data-md-color-scheme"],
    });
    new MutationObserver(pickColors).observe(document.documentElement, {
        attributes: true,
        attributeFilter: ["data-xnano-style"],
    });
}

function setupCollapsibleNavigation() {
    document.querySelectorAll("label.md-nav__link").forEach(labelLink => {
        const li = labelLink.closest("li.md-nav__item--nested");
        const label = labelLink.querySelector(".md-ellipsis");
        if (li && label) {
            const text = label.textContent.trim();
            if (
                text === "Session & Lifecycle" ||
                text === "User Triggered Hooks" ||
                text === "State & Grid Field Conditions" ||
                text === "Web Requests"
            ) {
                li.classList.add("xnano-hooks-subsection");
                const toggle = li.querySelector("input.md-nav__toggle");
                const navigation = li.querySelector("nav.md-nav");
                if (toggle) toggle.checked = true;
                if (navigation) navigation.setAttribute("aria-expanded", "true");
            }
            if (text === "Hooks & Actions") {
                li.classList.add("xnano-hooks-nav");
            }
            if (text === "Sandbox") {
                li.classList.add("xnano-sandbox-nav");
            }
            if (
                text === "Sandbox" ||
                text === "Hooks & Actions" ||
                text === "Components" ||
                text === "Beta" ||
                text === "Tutorials" ||
                text === "Core Architecture" ||
                text === "API Reference"
            ) {
                li.classList.remove("md-nav__item--section");
            }
        }
    });
}

function getContext7TableRows(text) {
    const sourceRows = text.trim().split(/\|\s+\|/);
    if (sourceRows.length < 3) return null;

    const rows = sourceRows.map((sourceRow, index) => {
        let row = sourceRow.trim();
        if (index === 0) row = row.replace(/^\|/, "");
        if (index === sourceRows.length - 1) row = row.replace(/\|$/, "");
        return row.split("|").map((cell) => cell.trim());
    });
    const columnCount = rows[0].length;
    const divider = rows[1];
    const isTable =
        columnCount > 1 &&
        rows.every((row) => row.length === columnCount) &&
        divider.every((cell) => /^:?-{3,}:?$/.test(cell));

    return isTable ? [rows[0], ...rows.slice(2)] : null;
}

function renderContext7Tables(shadowRoot) {
    shadowRoot.querySelectorAll(".c7-msg.assistant p").forEach((paragraph) => {
        const rows = getContext7TableRows(paragraph.textContent);
        if (!rows) return;

        const wrapper = document.createElement("div");
        const table = document.createElement("table");
        const tableHead = document.createElement("thead");
        const tableBody = document.createElement("tbody");

        wrapper.className = "c7-table-wrapper";
        rows.forEach((row, rowIndex) => {
            const tableRow = document.createElement("tr");
            row.forEach((cell) => {
                const tableCell = document.createElement(
                    rowIndex === 0 ? "th" : "td",
                );
                tableCell.textContent = cell;
                tableRow.appendChild(tableCell);
            });
            (rowIndex === 0 ? tableHead : tableBody).appendChild(tableRow);
        });

        table.appendChild(tableHead);
        table.appendChild(tableBody);
        wrapper.appendChild(table);
        paragraph.replaceWith(wrapper);
    });
}

function applyAppearancePreference(kind, value) {
    const attribute = kind === "style" ? "xnanoStyle" : "xnanoSize";
    const storageKey = kind === "style" ? "xnano-style" : "xnano-text-size";

    document.documentElement.dataset[attribute] = value;
    try {
        localStorage.setItem(storageKey, value);
    } catch (_) {}

    document
        .querySelectorAll(`[data-appearance-kind="${kind}"]`)
        .forEach((button) => {
            const isSelected = button.dataset.appearanceValue === value;
            button.classList.toggle("is-selected", isSelected);
            button.setAttribute("aria-pressed", String(isSelected));
        });

    const context7Host = document.getElementById("context7-widget");
    if (context7Host) context7Host.dataset[attribute] = value;
}

function setAppearanceMenuOpen(container, isOpen) {
    const button = container.querySelector(".xnano-appearance__button");
    const menu = container.querySelector(".xnano-appearance__menu");

    container.classList.toggle("is-open", isOpen);
    button.setAttribute("aria-expanded", String(isOpen));
    menu.hidden = !isOpen;
}

function setupAppearanceMenu() {
    let container = document.getElementById("xnano-appearance");

    if (!container) {
        container = document.createElement("div");
        container.id = "xnano-appearance";
        container.className = "xnano-appearance";
        container.innerHTML = `
            <button class="xnano-appearance__button" type="button"
                    aria-label="Open appearance settings" aria-expanded="false"
                    aria-controls="xnano-appearance-menu">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/>
                    <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V21h-4v-.08A1.7 1.7 0 0 0 8.94 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.57 15 1.7 1.7 0 0 0 3 14H3v-4h.08A1.7 1.7 0 0 0 4.6 8.94a1.7 1.7 0 0 0-.34-1.88L4.2 7l2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.57 1.7 1.7 0 0 0 10 3.08V3h4v.08A1.7 1.7 0 0 0 15.06 4.6a1.7 1.7 0 0 0 1.88-.34L17 4.2 19.8 7l-.06.06A1.7 1.7 0 0 0 19.4 9c.24.6.82 1 1.52 1H21v4h-.08c-.68 0-1.28.4-1.52 1Z"/>
                </svg>
            </button>
            <div class="xnano-appearance__menu" id="xnano-appearance-menu"
                 role="dialog" aria-label="Appearance settings" hidden>
                <div class="xnano-appearance__heading">Appearance</div>
                <fieldset>
                    <legend>Text size</legend>
                    <div class="xnano-appearance__segments xnano-appearance__segments--size">
                        <button type="button" data-appearance-kind="size" data-appearance-value="auto">Auto</button>
                        <button type="button" data-appearance-kind="size" data-appearance-value="small">Small</button>
                        <button type="button" data-appearance-kind="size" data-appearance-value="medium">Medium</button>
                        <button type="button" data-appearance-kind="size" data-appearance-value="large">Large</button>
                    </div>
                </fieldset>
                <fieldset>
                    <legend>Style</legend>
                    <div class="xnano-appearance__segments xnano-appearance__segments--style">
                        <button type="button" data-appearance-kind="style" data-appearance-value="mono">
                            <span class="xnano-appearance__sample xnano-appearance__sample--mono" aria-hidden="true">Aa</span>
                            <span>Mono</span>
                        </button>
                        <button type="button" data-appearance-kind="style" data-appearance-value="serif">
                            <span class="xnano-appearance__sample xnano-appearance__sample--serif" aria-hidden="true">Aa</span>
                            <span>Serif</span>
                        </button>
                        <button type="button" data-appearance-kind="style" data-appearance-value="modern">
                            <span class="xnano-appearance__sample xnano-appearance__sample--modern" aria-hidden="true">Aa</span>
                            <span>Modern</span>
                        </button>
                    </div>
                </fieldset>
            </div>`;
        document.body.appendChild(container);

        const toggle = container.querySelector(".xnano-appearance__button");
        toggle.addEventListener("click", () => {
            setAppearanceMenuOpen(
                container,
                toggle.getAttribute("aria-expanded") !== "true",
            );
        });
        container.querySelectorAll("[data-appearance-kind]").forEach((button) => {
            button.addEventListener("click", () => {
                applyAppearancePreference(
                    button.dataset.appearanceKind,
                    button.dataset.appearanceValue,
                );
            });
        });
        document.addEventListener("pointerdown", (event) => {
            if (!container.contains(event.target)) {
                setAppearanceMenuOpen(container, false);
            }
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && container.classList.contains("is-open")) {
                setAppearanceMenuOpen(container, false);
                toggle.focus();
            }
        });
    }

    applyAppearancePreference(
        "style",
        document.documentElement.dataset.xnanoStyle || "mono",
    );
    applyAppearancePreference(
        "size",
        document.documentElement.dataset.xnanoSize || "auto",
    );
}

function setupFloatingFooterAvoidance() {
    const updateKey = Symbol.for("xnano.footerAvoidanceUpdate");
    if (window[updateKey]) {
        window[updateKey]();
        return;
    }

    let frame = null;
    const updateOffset = () => {
        frame = null;
        const footer = document.querySelector(".md-footer");
        const footerTop = footer?.getBoundingClientRect().top ?? innerHeight;
        const lift = Math.max(0, innerHeight - footerTop);
        document.documentElement.style.setProperty(
            "--xnano-footer-lift",
            `${lift}px`,
        );
    };
    const requestUpdate = () => {
        if (frame === null) frame = requestAnimationFrame(updateOffset);
    };

    document.addEventListener("scroll", requestUpdate, { passive: true });
    window.addEventListener("resize", requestUpdate, { passive: true });
    window[updateKey] = requestUpdate;
    document.documentElement.dataset.xnanoFooterAvoidance = "true";
    requestUpdate();
}

async function setupContext7Widget() {
    const host = document.getElementById("context7-widget");
    const shadowRoot = window[Symbol.for("xnano.context7Shadow")];

    if (!host || !shadowRoot) return;

    const applyTheme = () => {
        host.dataset.theme = document.body.getAttribute("data-md-color-scheme");
        host.dataset.xnanoStyle =
            document.documentElement.dataset.xnanoStyle || "mono";
        host.dataset.xnanoSize =
            document.documentElement.dataset.xnanoSize || "auto";
    };

    applyTheme();

    if (!host.dataset.xnanoThemeObserver) {
        new MutationObserver(applyTheme).observe(document.body, {
            attributes: true,
            attributeFilter: ["data-md-color-scheme"],
        });
        host.dataset.xnanoThemeObserver = "true";
    }

    if (!host.dataset.xnanoMarkdownObserver) {
        const messages = shadowRoot.querySelector(".c7-messages");
        if (messages) {
            new MutationObserver(() => {
                renderContext7Tables(shadowRoot);
            }).observe(messages, { childList: true, subtree: true });
            renderContext7Tables(shadowRoot);
            host.dataset.xnanoMarkdownObserver = "true";
        }
    }

    if (shadowRoot.querySelector("style[data-xnano-context7]")) return;

    const stylesheetLink = document.querySelector(
        'link[href*="stylesheets/context7.css"]',
    );
    if (!stylesheetLink) return;

    const response = await fetch(stylesheetLink.href);
    if (!response.ok) return;

    const style = document.createElement("style");
    style.dataset.xnanoContext7 = "true";
    style.textContent = await response.text();
    shadowRoot.appendChild(style);
}

async function main() {
    setupTermynal();
    openLinksInNewTab();
    setupNavAccent();
    setupCollapsibleNavigation();
    setupAppearanceMenu();
    setupFloatingFooterAvoidance();
    await setupContext7Widget();
}

document$.subscribe(() => {
    main()
})

// The context7 chat widget renders inside a closed shadow root
// (attachShadow({ mode: "closed" })). Material's keyboard-shortcut
// handler resolves focus via `document.activeElement.shadowRoot`,
// which is null for closed roots, so it can't tell the widget's
// <input> is focused and fires "n"/"p"/etc page-navigation shortcuts
// while the user is typing a chat message. Shadow DOM event
// retargeting still exposes the host element as event.target to
// listeners outside the tree, so we can catch it here and stop the
// keydown before it reaches Material's document-level bubble
// listener (capture phase always runs before bubble phase).
//
// Enter is deliberately excluded: stopPropagation() during the
// capture phase kills the event for the *entire* path, including
// the widget's own send-on-Enter handling (widget.js falls back to
// a document-level keydown listener + composedPath() check, since
// the closed shadow root blocks it from using activeElement too).
// Blocking every key except Enter still stops Material's
// single-letter navigation shortcuts without silencing the send.
document.addEventListener(
    "keydown",
    (event) => {
        if (
            event.target?.id === "context7-widget" &&
            event.key !== "Enter"
        ) {
            event.stopPropagation();
        }
    },
    true,
);
