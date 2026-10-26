// Keeps the editorial chrome truthful: the header marks the section being read, and the
// construction diagram around the homepage wordmark shows its real rendered size.
(function () {
    "use strict";

    function markCurrentSection() {
        const wordmark = document.querySelector(".xn-wordmark");
        if (!wordmark) return;
        const root = new URL(wordmark.href, location.href).pathname;
        document.querySelectorAll(".xn-header__link[data-xn-section]").forEach((link) => {
            const section = root + link.dataset.xnSection;
            if (location.pathname.startsWith(section)) {
                link.setAttribute("aria-current", "page");
            } else {
                link.removeAttribute("aria-current");
            }
        });
    }

    let observer = null;

    function measureConstructions() {
        if (observer) observer.disconnect();
        const constructions = document.querySelectorAll(".xn-construct");
        if (!constructions.length || typeof ResizeObserver === "undefined") return;
        observer = new ResizeObserver((entries) => {
            for (const entry of entries) {
                const construction = entry.target.closest(".xn-construct");
                const box = entry.target.getBoundingClientRect();
                construction.querySelectorAll("[data-xn-measure]").forEach((label) => {
                    const size = label.dataset.xnMeasure === "width" ? box.width : box.height;
                    label.textContent = String(Math.round(size));
                });
            }
        });
        constructions.forEach((construction) => {
            const word = construction.querySelector(".xn-construct__word");
            if (word) observer.observe(word);
        });
    }

    const CHAPTER_CHOICES = "xnano.sidebar.chapters";

    function readChapterChoices() {
        try {
            return JSON.parse(sessionStorage.getItem(CHAPTER_CHOICES)) || {};
        } catch (error) {
            return {};
        }
    }

    function saveChapterChoice(title, isOpen) {
        const choices = readChapterChoices();
        choices[title] = isOpen;
        try {
            sessionStorage.setItem(CHAPTER_CHOICES, JSON.stringify(choices));
        } catch (error) {
            // Without storage, a choice lasts until the next page.
        }
    }

    // Chapters fold from their titles: reachable with Tab, toggled by a click, Enter or
    // Space. The chapter being read is always open. The others keep the reader's choice
    // for the rest of the visit, and until then only the first chapter is open.
    function makeChaptersFoldable() {
        const choices = readChapterChoices();
        const chapters = document.querySelectorAll(
            ".md-sidebar--primary .md-nav--primary > .md-nav__list > .md-nav__item--section",
        );
        chapters.forEach((item, index) => {
            const label = item.querySelector(":scope > .md-nav__link");
            const toggle = item.querySelector(":scope > .md-nav__toggle");
            if (!label || !toggle || label.dataset.xnOperable) return;
            label.dataset.xnOperable = "true";
            const title = label.textContent.trim();
            if (!toggle.checked) toggle.checked = title in choices ? choices[title] : index === 0;
            label.tabIndex = 0;
            label.setAttribute("role", "button");
            const sync = () => label.setAttribute("aria-expanded", String(toggle.checked));
            sync();
            toggle.addEventListener("change", () => {
                sync();
                saveChapterChoice(title, toggle.checked);
            });
            label.addEventListener("keydown", (event) => {
                if (event.key !== "Enter" && event.key !== " ") return;
                event.preventDefault();
                // The theme may toggle on Enter itself; only toggle when nothing else did.
                const before = toggle.checked;
                setTimeout(() => {
                    if (toggle.checked !== before) return;
                    toggle.checked = !before;
                    toggle.dispatchEvent(new Event("change", { bubbles: true }));
                });
            });
        });
    }

    function update() {
        markCurrentSection();
        measureConstructions();
        makeChaptersFoldable();
    }

    // With instant navigation, `document$` emits after every page change.
    if (typeof document$ !== "undefined") {
        document$.subscribe(update);
    } else if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", update);
    } else {
        update();
    }
})();
