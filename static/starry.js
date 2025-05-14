// static/starry.js
let animationFrameIdStarry;

function initStarrySky() {
    const starryBgDiv = document.getElementById('starry-bg');
    const canvas = document.getElementById('starry-canvas');

    if (!canvas || !starryBgDiv) {
        console.warn("Starry sky canvas or container not found.");
        return;
    }

    const isDarkMode = document.documentElement.getAttribute('data-bs-theme') === 'dark' || document.body.classList.contains('dark-mode');

    if (!isDarkMode) {
        starryBgDiv.style.display = 'none';
        if (animationFrameIdStarry) {
            cancelAnimationFrame(animationFrameIdStarry);
            animationFrameIdStarry = null;
        }
        canvas.dataset.starryInitialized = 'false';
        return;
    }

    if (canvas.dataset.starryInitialized === 'true') {
        starryBgDiv.style.display = 'block';
        if (!animationFrameIdStarry) animateStars();
        return;
    }

    const ctx = canvas.getContext('2d');
    canvas.dataset.starryInitialized = 'true';

    let stars = [];
    const numStars = window.innerWidth < 768 ? 60 : 120; // Adjusted star count

    function resizeStarryCanvas() {
        if (!starryBgDiv || !canvas) return;
        canvas.width = starryBgDiv.offsetWidth;
        canvas.height = starryBgDiv.offsetHeight;
        stars = [];
        for (let i = 0; i < numStars; i++) {
            stars.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                radius: Math.random() * 1.1 + 0.2, // Slightly smaller stars
                alpha: Math.random() * 0.7 + 0.2,  // Opacity
                vx: (Math.random() - 0.5) * 0.04, // Slower velocity
                vy: (Math.random() - 0.5) * 0.04
            });
        }
    }

    function drawStars() {
        if (!ctx || !canvas) return;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        // Purple stars
        ctx.fillStyle = 'rgba(155, 89, 182, 0.75)'; // Adjusted alpha for purple stars

        stars.forEach(star => {
            ctx.beginPath();
            ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
            ctx.globalAlpha = star.alpha;
            ctx.fill();

            star.x += star.vx;
            star.y += star.vy;

            if (star.x + star.radius < 0) star.x = canvas.width + star.radius;
            if (star.x - star.radius > canvas.width) star.x = -star.radius;
            if (star.y + star.radius < 0) star.y = canvas.height + star.radius;
            if (star.y - star.radius > canvas.height) star.y = -star.radius;
        });
        ctx.globalAlpha = 1.0;
    }

    function animateStars() {
        const currentIsDarkMode = document.documentElement.getAttribute('data-bs-theme') === 'dark' || document.body.classList.contains('dark-mode');
        if (!currentIsDarkMode) {
            if (animationFrameIdStarry) cancelAnimationFrame(animationFrameIdStarry);
            animationFrameIdStarry = null;
            if(starryBgDiv) starryBgDiv.style.display = 'none';
            canvas.dataset.starryInitialized = 'false';
            return;
        }
        if(starryBgDiv) starryBgDiv.style.display = 'block';
        drawStars();
        animationFrameIdStarry = requestAnimationFrame(animateStars);
    }

    console.log("Initializing starry sky for dark mode...");
    resizeStarryCanvas();
    if (animationFrameIdStarry) cancelAnimationFrame(animationFrameIdStarry);
    animateStars();

    let resizeTimeoutStarry;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeoutStarry);
        resizeTimeoutStarry = setTimeout(() => {
            const currentIsDarkModeOnResize = document.documentElement.getAttribute('data-bs-theme') === 'dark' || document.body.classList.contains('dark-mode');
            if (currentIsDarkModeOnResize) {
                 console.log("Resizing starry canvas due to window resize (dark mode active).");
                 resizeStarryCanvas();
                 if (!animationFrameIdStarry) animateStars();
            } else {
                if (animationFrameIdStarry) cancelAnimationFrame(animationFrameIdStarry);
                animationFrameIdStarry = null;
                if(starryBgDiv) starryBgDiv.style.display = 'none';
                if(canvas) canvas.dataset.starryInitialized = 'false';
            }
        }, 250);
    });
}

function stopStarrySky() {
    const starryBgDiv = document.getElementById('starry-bg');
    const canvas = document.getElementById('starry-canvas');
    if (animationFrameIdStarry) {
        cancelAnimationFrame(animationFrameIdStarry);
        animationFrameIdStarry = null;
        console.log("Starry sky animation explicitly stopped.");
    }
    if (starryBgDiv) starryBgDiv.style.display = 'none';
    if (canvas) canvas.dataset.starryInitialized = 'false';
}

window.initStarrySky = initStarrySky;
window.stopStarrySky = stopStarrySky;

// No initial call here; theme.js calls initStarrySky when dark mode is applied.
// However, if the page loads and localStorage already has 'dark', theme.js will call it.
