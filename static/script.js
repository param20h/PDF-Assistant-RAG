// Check for saved user preference, if any, on load of the website
document.addEventListener("DOMContentLoaded", () => {
    const currentTheme = localStorage.getItem("theme");
    if (currentTheme === "light") {
        document.body.classList.add("light-mode");
    }
});

// Expose toggle function to global scope
function toggleLightMode() {
    document.body.classList.toggle("light-mode");
    let theme = "dark";
    if (document.body.classList.contains("light-mode")) {
        theme = "light";
    }
    localStorage.setItem("theme", theme);
}