function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    if (sidebar) sidebar.classList.toggle("show");
}

document.addEventListener("click", function (event) {
    const sidebar = document.getElementById("sidebar");
    const toggle = document.querySelector(".mobile-toggle");
    if (!sidebar || !sidebar.classList.contains("show")) return;
    if (!sidebar.contains(event.target) && toggle && !toggle.contains(event.target)) {
        sidebar.classList.remove("show");
    }
});