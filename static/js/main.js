/**
 * VenomWatch — Core UI/UX Interactive Utilities
 * Smooth micro-interactions, accessible toast feedback, button states, and dashboard stats.
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
     * Show a modern non-blocking toast notification.
     * @param {string} message - Message text to display
     * @param {string} type - 'success' | 'error' | 'warning' | 'info'
     * @param {number} duration - Auto-dismiss delay in ms (default 4000)
     */
    window.showToast = function (message, type = 'info', duration = 4000) {
        const container = getToastContainer();

        const toast = document.createElement('div');
        toast.className = `vw-toast vw-toast-${type}`;

        const icons = {
            success: 'fa-circle-check',
            error: 'fa-circle-exclamation',
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
            if (toast.classList.contains('vw-toast-leaving')) return;
            toast.classList.add('vw-toast-leaving');
            setTimeout(() => {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 250);
        }

        closeBtn.addEventListener('click', removeToast);

        container.appendChild(toast);

        // Force reflow for CSS enter animation
        void toast.offsetWidth;
        toast.classList.add('vw-toast-visible');

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

        const counters = document.querySelectorAll('.stat-box h4, .stat-counter');
        counters.forEach(counter => {
            const rawText = counter.innerText.trim();
            const target = parseInt(rawText, 10);
            if (isNaN(target) || target <= 0) return;

            // Only animate if it's purely a number
            if (!/^\d+$/.test(rawText)) return;

            let start = 0;
            const duration = 400; // ms
            const startTime = performance.now();

            function updateCounter(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                // Ease out quad
                const easeProgress = 1 - (1 - progress) * (1 - progress);
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
    // 4. GLOBAL DOM INITIALIZATION
    // =========================================================================
    document.addEventListener('DOMContentLoaded', function () {
        // Run counter animations
        animateCounters();

        // Convert existing server flash messages into unified toasts if present
        const serverAlerts = document.querySelectorAll('.container > .alert[role="alert"]');
        if (serverAlerts.length > 0) {
            serverAlerts.forEach(alert => {
                let type = 'info';
                if (alert.classList.contains('alert-danger')) type = 'error';
                else if (alert.classList.contains('alert-success')) type = 'success';
                else if (alert.classList.contains('alert-warning')) type = 'warning';

                // Extract text excluding the close button
                const clone = alert.cloneNode(true);
                const btn = clone.querySelector('.btn-close');
                if (btn) btn.remove();
                const icon = clone.querySelector('i');
                if (icon) icon.remove();
                const text = clone.innerText.trim();

                if (text) {
                    window.showToast(text, type, 5000);
                    alert.style.display = 'none'; // hide in-place alert so toast handles it
                }
            });
        }

        // Keyboard Escape closes active overlays or detail panels
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                if (typeof window.resetPanel === 'function') {
                    window.resetPanel();
                }
            }
        });
    });

})();
