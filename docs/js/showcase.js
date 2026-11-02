// The homepage's showcase: a panel of recordings with one tab for each, as the
// `[data-xn-showcase]` figure in overrides/partials/home.html lays it out.
//
// - A click on a tab shows its panel and hides the others.
// - With the focus on a tab, the left and right arrow keys move to the previous and next
//   tab, and Home and End move to the first and last one, as the WAI-ARIA tabs pattern
//   describes.
// - A panel's recordings start again from their first frame when the panel is shown, so a
//   reader sees each game from its start.
(function () {
    "use strict";

    function restart(image) {
        const source = image.getAttribute("src");
        image.removeAttribute("loading");
        image.setAttribute("src", "");
        image.setAttribute("src", source);
    }

    function select(tabs, chosen) {
        for (const tab of tabs) {
            const isChosen = tab === chosen;
            const panel = document.getElementById(tab.getAttribute("aria-controls"));
            tab.setAttribute("aria-selected", isChosen ? "true" : "false");
            tab.tabIndex = isChosen ? 0 : -1;
            if (!panel) continue;
            const wasHidden = panel.hidden;
            panel.hidden = !isChosen;
            if (isChosen && wasHidden) panel.querySelectorAll("img").forEach(restart);
        }
    }

    function attach(showcase) {
        if (showcase.dataset.xnShowcaseReady) return;
        showcase.dataset.xnShowcaseReady = "true";
        const tabs = [...showcase.querySelectorAll('[role="tab"]')];
        tabs.forEach((tab, index) => {
            tab.addEventListener("click", () => select(tabs, tab));
            tab.addEventListener("keydown", (event) => {
                const moves = {
                    ArrowLeft: index - 1,
                    ArrowRight: index + 1,
                    Home: 0,
                    End: tabs.length - 1,
                };
                if (!(event.key in moves)) return;
                event.preventDefault();
                const next = tabs[(moves[event.key] + tabs.length) % tabs.length];
                select(tabs, next);
                next.focus();
            });
        });
    }

    function attachAll() {
        document.querySelectorAll("[data-xn-showcase]").forEach(attach);
    }

    // With instant navigation, `document$` emits after every page change.
    if (typeof document$ !== "undefined") {
        document$.subscribe(attachAll);
    } else if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", attachAll);
    } else {
        attachAll();
    }
})();
