// Adds the language of each highlighted code block to its header bar, creating the
// header when the block has no title.
(function () {
    "use strict";

    function formatLanguage(className) {
        return className
            .replace(/^language-/, "")
            .split(/[-+]+/)
            .filter(Boolean)
            .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
            .join("+");
    }

    function blockLanguage(block) {
        const languageClass = [...block.classList].find((name) => name.startsWith("language-"));
        return languageClass ? formatLanguage(languageClass) : null;
    }

    function addLanguageLabel(block) {
        const language = blockLanguage(block);
        if (!language) return;

        let header = block.querySelector(":scope > span.filename, :scope th.filename > span.filename");
        if (!header) {
            header = document.createElement("span");
            header.className = "filename";
            block.prepend(header);
        }

        let label = header.querySelector(":scope > span.code-lang");
        if (!label) {
            label = document.createElement("span");
            label.className = "code-lang";
            header.appendChild(label);
        }

        label.textContent = language;
    }

    function addLanguageLabels() {
        document.querySelectorAll(".highlight[class*='language-']").forEach(addLanguageLabel);
    }

    // With instant navigation, `document$` emits after every page change.
    if (typeof document$ !== "undefined") {
        document$.subscribe(addLanguageLabels);
    } else if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", addLanguageLabels);
    } else {
        addLanguageLabels();
    }
})();
