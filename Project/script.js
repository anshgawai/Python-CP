(function () {
    function markExternalState() {
        var parentDocument = window.parent && window.parent.document;
        if (!parentDocument) return;

        var navbar = parentDocument.querySelector(".top-navbar");
        if (!navbar) return;

        var activePage = navbar.getAttribute("data-active-page");
        parentDocument.title = activePage
            ? activePage + " | AI Data Analyzer"
            : "AI Data Analyzer";
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", markExternalState);
    } else {
        markExternalState();
    }
})();
