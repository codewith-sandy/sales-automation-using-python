(() => {
    const glow = document.querySelector('.interactive-bg .cursor-glow');
    if (!glow) {
        return;
    }

    const moveGlow = (x, y) => {
        glow.style.left = `${x}px`;
        glow.style.top = `${y}px`;
    };

    document.addEventListener('mousemove', (event) => {
        moveGlow(event.clientX, event.clientY);
    });

    document.addEventListener('touchmove', (event) => {
        if (event.touches && event.touches[0]) {
            moveGlow(event.touches[0].clientX, event.touches[0].clientY);
        }
    }, { passive: true });
})();
