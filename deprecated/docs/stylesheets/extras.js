document.addEventListener("DOMContentLoaded", function () {
  const siteName = document.querySelector(".md-header__title .md-ellipsis");
  if (siteName) {
    const text = siteName.textContent;
    const index = text.indexOf("zyx");
    if (index !== -1) {
      siteName.innerHTML =
        text.slice(0, index) +
        'zy<span style="color: #60AAF2;">x</span>' +
        text.slice(index + 3);
    }
  }
});
