(function () {
    "use strict";

    function bindShowcase(element) {
        if (element.dataset.xnanoShowcaseBound === "1") {
            return;
        }
        element.dataset.xnanoShowcaseBound = "1";

        function showColor() {
            element.classList.add("is-color");
        }

        function showMono() {
            element.classList.remove("is-color");
        }

        element.addEventListener("mouseenter", showColor);
        element.addEventListener("mouseleave", showMono);
        element.addEventListener("focusin", showColor);
        element.addEventListener("focusout", function (event) {
            if (!element.contains(event.relatedTarget)) {
                showMono();
            }
        });
        element.addEventListener(
            "touchstart",
            function () {
                showColor();
            },
            { passive: true }
        );
    }

    function initShowcaseHover() {
        document.querySelectorAll(".xnano-showcase").forEach(bindShowcase);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initShowcaseHover);
    } else {
        initShowcaseHover();
    }

    document.addEventListener("MDContentSwitch", initShowcaseHover);
    document.addEventListener("DOMContentSwitch", initShowcaseHover);
})();