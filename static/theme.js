// static/theme.js
document.addEventListener('DOMContentLoaded', () => {
    const themeToggleButton = document.getElementById('theme-toggle-btn');
    const htmlElement = document.documentElement; // Target <html> for Bootstrap's data-bs-theme
    const bodyElement = document.body; // Target <body> for our custom .dark-mode class (optional redundancy)
    const starryBgDiv = document.getElementById('starry-bg'); // Get starry background div

    const sunIconHTML = '<i class="fas fa-sun"></i> <span class="d-none d-md-inline">Light Mode</span>';
    const moonIconHTML = '<i class="fas fa-moon"></i> <span class="d-none d-md-inline">Dark Mode</span>';

    // Function to apply the theme
    const applyTheme = (theme) => {
        if (theme === 'dark') {
            htmlElement.setAttribute('data-bs-theme', 'dark');
            bodyElement.classList.add('dark-mode'); // Add our custom class if needed for non-Bootstrap components
            if (themeToggleButton) themeToggleButton.innerHTML = sunIconHTML;

            if (starryBgDiv) { // Ensure starryBgDiv exists
                starryBgDiv.style.display = 'block'; // Show starry background
                if (window.initStarrySky && typeof window.initStarrySky === 'function') {
                    window.initStarrySky(); // Initialize or ensure starry sky is running
                }
            }
        } else { // Light theme
            htmlElement.setAttribute('data-bs-theme', 'light');
            bodyElement.classList.remove('dark-mode');
            if (themeToggleButton) themeToggleButton.innerHTML = moonIconHTML;

            if (starryBgDiv) { // Ensure starryBgDiv exists
                starryBgDiv.style.display = 'none'; // Hide starry background
                // Optionally stop starry sky animation if it's intensive
                if (window.stopStarrySky && typeof window.stopStarrySky === 'function') {
                     window.stopStarrySky();
                }
            }
        }
        console.log("Theme applied:", theme);
    };

    // Load saved theme from localStorage or use system preference
    let preferredTheme = localStorage.getItem('theme');
    if (!preferredTheme) {
        // If no theme saved, check system preference
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            preferredTheme = 'dark';
        } else {
            preferredTheme = 'light'; // Default to light if no preference or system preference
        }
    }
    applyTheme(preferredTheme);

    // Theme toggle button event listener
    if (themeToggleButton) {
        themeToggleButton.addEventListener('click', () => {
            // Determine current theme based on the htmlElement attribute
            let currentTheme = htmlElement.getAttribute('data-bs-theme') || 'light';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

            localStorage.setItem('theme', newTheme);
            applyTheme(newTheme);
        });
    } else {
        console.warn("Theme toggle button not found.");
    }

    // Listen for changes in system color scheme preference (optional)
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
            // Only change if no theme is explicitly saved by the user
            if (!localStorage.getItem('theme')) {
                const newSystemTheme = event.matches ? "dark" : "light";
                console.log("System theme changed to:", newSystemTheme);
                applyTheme(newSystemTheme);
            }
        });
    }
});
