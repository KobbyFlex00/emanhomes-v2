(function () {
    'use strict';

    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function setupHero(hero) {
        var slides = Array.prototype.slice.call(hero.querySelectorAll('.edge-hero__slide'));
        var dots = Array.prototype.slice.call(hero.querySelectorAll('[data-hero-slide]'));
        var captions = Array.prototype.slice.call(hero.querySelectorAll('[data-hero-caption]'));
        var interval = Number(hero.dataset.interval) || 45000;
        if (slides.length < 2) return;
        var current = 0;
        var timer;

        function show(index) {
            current = (index + slides.length) % slides.length;
            slides.forEach(function (slide, i) { slide.classList.toggle('is-active', i === current); });
            dots.forEach(function (dot, i) {
                dot.classList.toggle('is-active', i === current);
                dot.setAttribute('aria-current', i === current ? 'true' : 'false');
            });
            captions.forEach(function (caption, i) {
                var active = i === current;
                caption.classList.toggle('is-active', active);
                // Only the visible caption can be reached by keyboard or screen reader.
                if (active) { caption.removeAttribute('tabindex'); caption.removeAttribute('aria-hidden'); }
                else { caption.setAttribute('tabindex', '-1'); caption.setAttribute('aria-hidden', 'true'); }
            });
        }
        function restart() {
            window.clearInterval(timer);
            if (!reducedMotion) timer = window.setInterval(function () { show(current + 1); }, interval);
        }
        dots.forEach(function (dot, i) { dot.addEventListener('click', function () { show(i); restart(); }); });
        hero.addEventListener('mouseenter', function () { window.clearInterval(timer); });
        hero.addEventListener('mouseleave', restart);
        hero.addEventListener('keydown', function (event) {
            if (event.key === 'ArrowRight') { show(current + 1); restart(); }
            if (event.key === 'ArrowLeft') { show(current - 1); restart(); }
        });
        show(0);
        restart();
    }

    function setupCarousels() {
        document.querySelectorAll('[data-carousel]').forEach(function (shell) {
            var track = shell.querySelector('.carousel-track');
            var previous = shell.querySelector('[data-carousel-prev]');
            var next = shell.querySelector('[data-carousel-next]');
            if (!track || !previous || !next) return;
            function distance() { return Math.max(track.clientWidth * .82, 280); }
            function update() {
                previous.disabled = track.scrollLeft <= 4;
                next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 4;
            }
            previous.addEventListener('click', function () { track.scrollBy({ left: -distance(), behavior: 'smooth' }); });
            next.addEventListener('click', function () { track.scrollBy({ left: distance(), behavior: 'smooth' }); });
            track.addEventListener('scroll', update, { passive: true });
            window.addEventListener('resize', update);
            update();
        });
    }

    function setupReveals() {
        var elements = document.querySelectorAll('.reveal-on-scroll');
        if (!('IntersectionObserver' in window) || reducedMotion) {
            elements.forEach(function (element) { element.classList.add('is-visible'); });
            return;
        }
        var observer = new IntersectionObserver(function (entries, instance) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) { entry.target.classList.add('is-visible'); instance.unobserve(entry.target); }
            });
        }, { threshold: .12 });
        elements.forEach(function (element) { observer.observe(element); });
    }

    function setupCounters() {
        document.querySelectorAll('[data-counter]').forEach(function (element) {
            var target = Number(element.dataset.counter);
            if (!target || reducedMotion) { element.textContent = target || 0; return; }
            var start = 0;
            var duration = 900;
            var started = null;
            function tick(timestamp) {
                if (!started) started = timestamp;
                var progress = Math.min((timestamp - started) / duration, 1);
                element.textContent = Math.floor(progress * target);
                if (progress < 1) window.requestAnimationFrame(tick);
            }
            if ('IntersectionObserver' in window) {
                var observer = new IntersectionObserver(function (entries, instance) {
                    if (entries[0].isIntersecting) { window.requestAnimationFrame(tick); instance.disconnect(); }
                });
                observer.observe(element);
            } else { element.textContent = target; }
        });
    }

    function setupAutoSubmit() {
        // Selects marked data-autosubmit apply immediately; the Apply button remains for no-JS visitors.
        document.querySelectorAll('select[data-autosubmit]').forEach(function (select) {
            select.addEventListener('change', function () { select.form.submit(); });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        setupAutoSubmit();
        document.querySelectorAll('[data-hero-carousel]').forEach(setupHero);
        setupCarousels();
        setupReveals();
        setupCounters();
    });
}());
