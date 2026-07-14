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
    };

    function pickColors() {
        const scheme = document.body.getAttribute("data-md-color-scheme");
        const palette = palettes[scheme] || palettes.slate;
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
}

function setupCollapsibleNavigation() {
    document.querySelectorAll("li.md-nav__item--section").forEach(li => {
        const label = li.querySelector("label.md-nav__link .md-ellipsis");
        if (label) {
            const text = label.textContent.trim();
            if (
                text === "Sandbox" ||
                text === "Components" ||
                text === "Tutorials" ||
                text === "Core Architecture" ||
                text === "API Reference"
            ) {
                li.classList.remove("md-nav__item--section");
            }
        }
    });
}

async function main() {
    setupTermynal();
    openLinksInNewTab();
    setupNavAccent();
    setupCollapsibleNavigation();
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
document.addEventListener(
    "keydown",
    (event) => {
        if (event.target?.id === "context7-widget") {
            event.stopPropagation();
        }
    },
    true,
);
