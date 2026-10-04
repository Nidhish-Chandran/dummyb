/**
 * VenomWatch — Core UI/UX Interactive Utilities
 * Smooth micro-interactions, accessible toast feedback, glassmorphic navbar effects,
 * button states, back-to-top handler, and animated dashboard stats.
 */

(function () {
    'use strict';

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // =========================================================================
    // 1. REUSABLE TOAST NOTIFICATION SYSTEM
    // =========================================================================
    function getToastContainer() {
        let container = document.getElementById('vwToastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'vwToastContainer';
            container.className = 'vw-toast-container';
            container.setAttribute('aria-live', 'polite');
            container.setAttribute('aria-atomic', 'true');
            document.body.appendChild(container);
        }
        return container;
    }

    /**
     * Show a modern non-blocking glass toast notification.
     * @param {string} message - Message text to display
     * @param {string} type - 'success' | 'error' | 'warning' | 'info'
     * @param {number} duration - Auto-dismiss delay in ms (default 4500)
     */
    window.showToast = function (message, type = 'info', duration = 4500) {
        const container = getToastContainer();

        const toast = document.createElement('div');
        toast.className = `vw-toast vw-toast-${type}`;

        const icons = {
            success: 'fa-circle-check',
            error: 'fa-triangle-exclamation',
            warning: 'fa-triangle-exclamation',
            info: 'fa-circle-info'
        };
        const iconClass = icons[type] || icons.info;

        toast.innerHTML = `
            <div class="vw-toast-icon">
                <i class="fa-solid ${iconClass}"></i>
            </div>
            <div class="vw-toast-content">
                <p class="vw-toast-message">${message}</p>
            </div>
            <button type="button" class="vw-toast-close" aria-label="Close notification">
                <i class="fa-solid fa-xmark"></i>
            </button>
        `;

        const closeBtn = toast.querySelector('.vw-toast-close');
        function removeToast() {
            if (toast.classList.contains('toast-dismissing')) return;
            toast.classList.add('toast-dismissing');
            setTimeout(() => {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 260);
        }

        closeBtn.addEventListener('click', removeToast);
        container.appendChild(toast);

        if (duration > 0) {
            setTimeout(removeToast, duration);
        }

        return toast;
    };

    // =========================================================================
    // 2. BUTTON LOADING STATE HELPER
    // =========================================================================
    window.setButtonLoading = function (button, isLoading, loadingText = '') {
        if (!button) return;
        if (isLoading) {
            button.dataset.originalHtml = button.innerHTML;
            button.classList.add('is-loading');
            button.disabled = true;
            if (loadingText) {
                button.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>${loadingText}`;
            }
        } else {
            button.classList.remove('is-loading');
            button.disabled = false;
            if (button.dataset.originalHtml) {
                button.innerHTML = button.dataset.originalHtml;
                delete button.dataset.originalHtml;
            }
        }
    };

    // =========================================================================
    // 3. DASHBOARD NUMBER COUNTER ANIMATION
    // =========================================================================
    function animateCounters() {
        if (prefersReducedMotion) return;

        const counters = document.querySelectorAll('.stat-box h4, .stat-counter, .stat-number');
        counters.forEach(counter => {
            const rawText = counter.innerText.trim();
            const target = parseInt(rawText, 10);
            if (isNaN(target) || target <= 0) return;

            // Only animate if it's purely a number
            if (!/^\d+$/.test(rawText)) return;

            const duration = 500; // ms
            const startTime = performance.now();

            function updateCounter(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                // Ease out cubic
                const easeProgress = 1 - Math.pow(1 - progress, 3);
                const current = Math.floor(easeProgress * target);
                counter.innerText = current;

                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.innerText = target;
                }
            }

            counter.innerText = '0';
            requestAnimationFrame(updateCounter);
        });
    }

    // =========================================================================
    // 4. NAVBAR SCROLL & BACK TO TOP BEHAVIOR
    // =========================================================================
    function initNavigationEffects() {
        const navbar = document.getElementById('mainNav');
        const backToTopBtn = document.getElementById('backToTopBtn');

        let lastScrollY = window.scrollY;

        function handleScroll() {
            const currentScrollY = window.scrollY;

            // Navbar shrink & enhanced blur
            if (navbar) {
                if (currentScrollY > 20) {
                    navbar.classList.add('navbar-scrolled');
                } else {
                    navbar.classList.remove('navbar-scrolled');
                }
            }

            // Back to top visibility
            if (backToTopBtn) {
                if (currentScrollY > 320) {
                    backToTopBtn.classList.add('visible');
                } else {
                    backToTopBtn.classList.remove('visible');
                }
            }

            lastScrollY = currentScrollY;
        }

        window.addEventListener('scroll', handleScroll, { passive: true });
        handleScroll(); // Initial check

        if (backToTopBtn) {
            backToTopBtn.addEventListener('click', function () {
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            });
        }
    }

    // =========================================================================
    // 5. MOBILE DRAWER AUTO-CLOSE & INTERACTIVITY
    // =========================================================================
    function initMobileNav() {
        const navbarCollapse = document.getElementById('venomNavbar');
        if (!navbarCollapse) return;

        // Auto close when clicking any navigation link on mobile
        const navLinks = navbarCollapse.querySelectorAll('.nav-link, .btn');
        navLinks.forEach(link => {
            link.addEventListener('click', function () {
                if (window.innerWidth < 992 && navbarCollapse.classList.contains('show')) {
                    const bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse);
                    if (bsCollapse) bsCollapse.hide();
                }
            });
        });
    }

    // =========================================================================
    // 6. GLOBAL DOM INITIALIZATION
    // =========================================================================
    document.addEventListener('DOMContentLoaded', function () {
        // Initialize Navigation Enhancements
        initNavigationEffects();
        initMobileNav();

        // Run metric counters
        animateCounters();

        // Convert existing server flash messages into toasts
        const serverAlerts = document.querySelectorAll('.container > .alert[role="alert"]');
        if (serverAlerts.length > 0) {
            serverAlerts.forEach(alert => {
                let type = 'info';
                if (alert.classList.contains('alert-danger')) type = 'error';
                else if (alert.classList.contains('alert-success')) type = 'success';
                else if (alert.classList.contains('alert-warning')) type = 'warning';

                const clone = alert.cloneNode(true);
                const btn = clone.querySelector('.btn-close');
                if (btn) btn.remove();
                const icon = clone.querySelector('i');
                if (icon) icon.remove();
                const text = clone.innerText.trim();

                if (text) {
                    window.showToast(text, type, 5000);
                    alert.style.display = 'none';
                }
            });
        }

        // Global Escape key dismisses overlays
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                if (typeof window.resetPanel === 'function') {
                    window.resetPanel();
                }
            }
        });
    });

})();
