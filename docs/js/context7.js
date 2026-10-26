// Dresses the Context7 chat widget in the editorial theme: its stylesheet is added to the
// widget's shadow root, the widget follows the light or dark scheme, markdown tables in
// answers become real tables, and typing in it never triggers the site's shortcut keys.
(function () {
    "use strict";

    const stylesheetUrl = new URL("../stylesheets/editorial/context7.css", document.currentScript.src).href;
    const shadowKey = Symbol.for("xnano.context7Shadow");

    function tableRows(text) {
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

    function renderTables(shadowRoot) {
        shadowRoot.querySelectorAll(".c7-msg.assistant p").forEach((paragraph) => {
            const rows = tableRows(paragraph.textContent);
            if (!rows) return;
            const wrapper = document.createElement("div");
            const table = document.createElement("table");
            const head = document.createElement("thead");
            const body = document.createElement("tbody");
            wrapper.className = "c7-table-wrapper";
            rows.forEach((row, rowIndex) => {
                const tableRow = document.createElement("tr");
                row.forEach((cell) => {
                    const tableCell = document.createElement(rowIndex === 0 ? "th" : "td");
                    tableCell.textContent = cell;
                    tableRow.appendChild(tableCell);
                });
                (rowIndex === 0 ? head : body).appendChild(tableRow);
            });
            table.append(head, body);
            wrapper.appendChild(table);
            paragraph.replaceWith(wrapper);
        });
    }

    async function dress(host, shadowRoot) {
        const followScheme = () => {
            host.dataset.theme = document.body.getAttribute("data-md-color-scheme");
        };
        followScheme();
        new MutationObserver(followScheme).observe(document.body, {
            attributes: true,
            attributeFilter: ["data-md-color-scheme"],
        });

        const watchMessages = () => {
            const messages = shadowRoot.querySelector(".c7-messages");
            if (!messages) return false;
            new MutationObserver(() => renderTables(shadowRoot)).observe(messages, {
                childList: true,
                subtree: true,
            });
            renderTables(shadowRoot);
            return true;
        };
        if (!watchMessages()) {
            const waiting = new MutationObserver(() => {
                if (watchMessages()) waiting.disconnect();
            });
            waiting.observe(shadowRoot, { childList: true, subtree: true });
        }

        if (shadowRoot.querySelector("style[data-xnano-context7]")) return;
        const response = await fetch(stylesheetUrl);
        if (!response.ok) return;
        const style = document.createElement("style");
        style.dataset.xnanoContext7 = "true";
        style.textContent = await response.text();
        shadowRoot.appendChild(style);
    }

    // widget.js loads after this script, so wait for its host and shadow root to appear.
    function whenReady() {
        const host = document.getElementById("context7-widget");
        const shadowRoot = window[shadowKey];
        if (host && shadowRoot) {
            dress(host, shadowRoot);
            return true;
        }
        return false;
    }

    if (!whenReady()) {
        const waiting = new MutationObserver(() => {
            if (whenReady()) waiting.disconnect();
        });
        waiting.observe(document.documentElement, { childList: true, subtree: true });
    }

    // The widget's input lives in a closed shadow root, so the site cannot see that it has
    // focus and would treat letters typed into it as navigation shortcuts. Stop those keys at
    // the host; Enter passes through so the widget can still send the message.
    document.addEventListener(
        "keydown",
        (event) => {
            if (event.target?.id === "context7-widget" && event.key !== "Enter") {
                event.stopPropagation();
            }
        },
        true,
    );
})();
