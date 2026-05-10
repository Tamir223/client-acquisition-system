'use strict';

// ─── Canvas Particle Background ──────────────────────────────────────────────
(function () {
    const canvas = document.createElement('canvas');
    canvas.id = 'bg-canvas';
    document.body.prepend(canvas);
    const ctx = canvas.getContext('2d');

    let W = 0, H = 0;
    let vignette = null;

    function buildVignette() {
        vignette = ctx.createRadialGradient(W / 2, H * 0.45, H * 0.05, W / 2, H * 0.45, H * 0.75);
        vignette.addColorStop(0, 'rgba(10,15,30,0)');
        vignette.addColorStop(1, 'rgba(10,15,30,0.55)');
    }

    function resize() {
        W = canvas.width  = window.innerWidth;
        H = canvas.height = window.innerHeight;
        buildVignette();
    }

    resize();
    window.addEventListener('resize', () => {
        resize();
        particles.forEach(p => p.scatter());
    });

    // ─── Particles ───
    const PARTICLE_COUNT = 150;

    class Particle {
        scatter() {
            this.x    = Math.random() * W;
            this.y    = Math.random() * H;
            this.r    = 0.5 + Math.random() * 2;           // 0.5–2.5 px
            this.o    = 0.3  + Math.random() * 0.7;        // 0.3–1.0 opacity
            const spd = 0.04 + Math.random() * 0.09;       // ultra slow
            const ang = Math.random() * Math.PI * 2;
            this.vx   = Math.cos(ang) * spd;
            this.vy   = Math.sin(ang) * spd;
            this.blue = Math.random() > 0.72;
        }
        constructor() { this.scatter(); }
        update() {
            this.x += this.vx;
            this.y += this.vy;
            if (this.x < -6)    this.x = W + 6;
            if (this.x > W + 6) this.x = -6;
            if (this.y < -6)    this.y = H + 6;
            if (this.y > H + 6) this.y = -6;
        }
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
            ctx.fillStyle = this.blue
                ? `rgba(79,195,247,${this.o})`
                : `rgba(255,255,255,${this.o})`;
            ctx.fill();
        }
    }

    const particles = Array.from({ length: PARTICLE_COUNT }, () => new Particle());

    // ─── Geometric Shapes ───
    const GEO_COUNT = 3 + Math.floor(Math.random() * 3); // 3–5

    class GeoShape {
        constructor() {
            this.x     = 80  + Math.random() * (W - 160);
            this.y     = 80  + Math.random() * (H - 160);
            this.r     = 80  + Math.random() * 140;
            this.rot   = Math.random() * Math.PI * 2;
            this.speed = (Math.random() > 0.5 ? 1 : -1) * (0.0006 + Math.random() * 0.0014);
            this.o     = 0.014 + Math.random() * 0.028;
            this.isHex = Math.random() > 0.4;
        }
        update() { this.rot += this.speed; }
        draw() {
            ctx.save();
            ctx.globalAlpha = this.o;
            ctx.strokeStyle = '#4fc3f7';
            ctx.lineWidth   = 0.5;
            ctx.beginPath();
            if (this.isHex) {
                for (let i = 0; i < 6; i++) {
                    const a  = this.rot + (i * Math.PI * 2) / 6;
                    const px = this.x + this.r * Math.cos(a);
                    const py = this.y + this.r * Math.sin(a);
                    i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
                }
                ctx.closePath();
            } else {
                ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
            }
            ctx.stroke();
            ctx.restore();
        }
    }

    const geoShapes = Array.from({ length: GEO_COUNT }, () => new GeoShape());

    // ─── Shooting Star ───
    class ShootingStar {
        constructor() { this.active = false; this.tail = []; }
        activate() {
            this.x       = Math.random() * W * 0.6;
            this.y       = Math.random() * H * 0.3;
            const angle  = (12 + Math.random() * 28) * Math.PI / 180;
            const spd    = 9  + Math.random() * 7;
            this.vx      = Math.cos(angle) * spd;
            this.vy      = Math.sin(angle) * spd;
            this.tail    = [];
            this.maxLen  = 28;
            this.opacity = 1;
            this.active  = true;
        }
        update() {
            if (!this.active) return;
            this.tail.unshift({ x: this.x, y: this.y });
            if (this.tail.length > this.maxLen) this.tail.pop();
            this.x += this.vx;
            this.y += this.vy;
            this.opacity -= 0.016;
            if (this.opacity <= 0 || this.x > W + 60 || this.y > H + 60) {
                this.active = false;
                this.tail   = [];
            }
        }
        draw() {
            if (!this.active || this.tail.length < 2) return;
            for (let i = 0; i < this.tail.length - 1; i++) {
                const ratio = 1 - i / this.tail.length;
                ctx.beginPath();
                ctx.moveTo(this.tail[i].x,     this.tail[i].y);
                ctx.lineTo(this.tail[i + 1].x, this.tail[i + 1].y);
                ctx.strokeStyle = `rgba(220,240,255,${ratio * this.opacity})`;
                ctx.lineWidth   = ratio * 2;
                ctx.stroke();
            }
            // Bright head
            ctx.beginPath();
            ctx.arc(this.x, this.y, 1.8, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255,255,255,${this.opacity})`;
            ctx.fill();
        }
    }

    const star       = new ShootingStar();
    let lastStarTime = -999999;
    let nextStarIn   = 8000 + Math.random() * 4000; // 8–12s first appearance

    // ─── Animation Loop ───
    function draw(ts) {
        ctx.clearRect(0, 0, W, H);

        // Deep space base
        ctx.fillStyle = '#0a0f1e';
        ctx.fillRect(0, 0, W, H);

        // Faint rotating geometrics
        geoShapes.forEach(s => { s.update(); s.draw(); });

        // Particle field
        particles.forEach(p => { p.update(); p.draw(); });

        // Shooting star
        if (!star.active && ts - lastStarTime > nextStarIn) {
            star.activate();
            lastStarTime = ts;
            nextStarIn   = 8000 + Math.random() * 4000;
        }
        star.update();
        star.draw();

        // Vignette overlay for text readability
        if (vignette) {
            ctx.fillStyle = vignette;
            ctx.fillRect(0, 0, W, H);
        }

        requestAnimationFrame(draw);
    }

    requestAnimationFrame(draw);
}());


// ─── DOM-Ready: Scroll Reveal + FAQ + Form ───────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

    // ── Scroll Reveal ──
    function initReveal() {
        // Section headings
        document.querySelectorAll(
            '.problem h2, .how-it-works h2, .timeline h2, .offer h2, .testimonials h2, .faq h2, .contact h2'
        ).forEach(el => el.classList.add('reveal'));

        // Section subtitles (below the fold only — hero subheadline is excluded)
        document.querySelectorAll('.section-sub').forEach(el => {
            el.classList.add('reveal');
            el.style.transitionDelay = '80ms';
        });

        // Stat cards: scale pop
        document.querySelectorAll('.stat').forEach((el, i) => {
            el.classList.add('reveal-scale');
            el.style.transitionDelay = `${i * 110}ms`;
        });

        // How It Works steps: staggered fade-up
        document.querySelectorAll('.step').forEach((el, i) => {
            el.classList.add('reveal');
            el.style.transitionDelay = `${i * 120}ms`;
        });

        // Timeline steps: staggered fade-up
        document.querySelectorAll('.timeline-step').forEach((el, i) => {
            el.classList.add('reveal');
            el.style.transitionDelay = `${i * 120}ms`;
        });

        // Testimonials: slide in from right
        document.querySelectorAll('.testimonial').forEach((el, i) => {
            el.classList.add('reveal-right');
            el.style.transitionDelay = `${i * 110}ms`;
        });

        // FAQ items: slide in from left
        document.querySelectorAll('.faq-item').forEach((el, i) => {
            el.classList.add('reveal-left');
            el.style.transitionDelay = `${i * 80}ms`;
        });

        // Pricing card elements: staggered fade-up
        ['.offer-badge', '.offer-price', '.offer-features', '.offer-cta', '.offer-note'].forEach((sel, i) => {
            const el = document.querySelector(sel);
            if (el) {
                el.classList.add('reveal');
                el.style.transitionDelay = `${i * 90}ms`;
            }
        });

        // Trust bar (hero, immediately visible — slight delay for polish)
        const trustBar = document.querySelector('.trust-bar');
        if (trustBar) {
            trustBar.classList.add('reveal');
            trustBar.style.transitionDelay = '180ms';
        }

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -30px 0px' });

        document.querySelectorAll('.reveal, .reveal-scale, .reveal-left, .reveal-right')
            .forEach(el => observer.observe(el));
    }

    initReveal();

    // ── FAQ Accordion ──
    document.querySelectorAll('.faq-question').forEach((btn) => {
        btn.addEventListener('click', () => {
            const item   = btn.closest('.faq-item');
            const isOpen = item.classList.contains('open');

            document.querySelectorAll('.faq-item.open').forEach((el) => {
                el.classList.remove('open');
                el.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
            });

            if (!isOpen) {
                item.classList.add('open');
                btn.setAttribute('aria-expanded', 'true');
            }
        });
    });

    // ── Lead Capture Form ──
    const form      = document.getElementById('lead-form');
    const messageEl = document.getElementById('form-message');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn    = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Sending...';
        submitBtn.disabled    = true;
        messageEl.textContent = '';
        messageEl.className   = 'form-message';

        const payload = {
            first_name: form.first_name.value.trim(),
            last_name:  form.last_name.value.trim(),
            email:      form.email.value.trim(),
            company:    form.company.value.trim(),
            phone:      form.phone.value.trim(),
            niche:      form.niche.value.trim(),
        };

        try {
            const res  = await fetch('/api/lead', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            const data = await res.json();

            if (res.ok) {
                messageEl.textContent = "Got it! We'll be in touch within 24 hours.";
                messageEl.classList.add('success');
                form.reset();
            } else {
                throw new Error(data.error || 'Something went wrong.');
            }
        } catch (err) {
            messageEl.textContent = err.message || 'Something went wrong. Please try again.';
            messageEl.classList.add('error');
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled    = false;
        }
    });
});

