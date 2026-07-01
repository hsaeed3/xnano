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

    function getLanguage(block) {
        const langClass = [...block.classList].find((name) => name.startsWith("language-"));
        return langClass ? formatLanguage(langClass) : null;
    }

    function ensureLanguageLabel(block) {
        const language = getLanguage(block);
        if (!language) return;

        let header = block.querySelector(":scope > span.filename");
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

    function initCodeLang() {
        document.querySelectorAll(".highlight[class*='language-']").forEach(ensureLanguageLabel);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initCodeLang);
    } else {
        initCodeLang();
    }

    document.addEventListener("DOMContentSwitch", initCodeLang);
})();
