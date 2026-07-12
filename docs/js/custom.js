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

// Picks two random colors from the current theme's aurora palette (shared
// with hero.js) once per page load and hands them to nav.css as CSS vars.
// This is a single synchronous pick — no animation loop, no per-frame cost.
function setupNavAccent() {
    const palettes = window.__xnanoAuroraPalettes;
    if (!palettes) return;

    // Lighten by mixing toward white — keeps the same hue, just a lighter
    // tint of it, rather than jumping to an unrelated color in the palette.
    function lighten([r, g, b], amount) {
        return [r, g, b].map(v => Math.round(v + (255 - v) * amount));
    }

    function pickColors() {
        const scheme = document.body.getAttribute("data-md-color-scheme");
        const palette = palettes[scheme] || palettes.slate;
        const base = palette[Math.floor(Math.random() * palette.length)];
        const toRgb = ([r, g, b]) => `rgb(${r}, ${g}, ${b})`;
        document.documentElement.style.setProperty("--xnano-nav-c1", toRgb(base));
        document.documentElement.style.setProperty("--xnano-nav-c2", toRgb(lighten(base, 0.45)));
    }

    pickColors();
    new MutationObserver(pickColors).observe(document.body, {
        attributes: true,
        attributeFilter: ["data-md-color-scheme"],
    });
}

async function main() {
    setupTermynal();
    openLinksInNewTab();
    setupNavAccent();
}

document$.subscribe(() => {
    main()
})
