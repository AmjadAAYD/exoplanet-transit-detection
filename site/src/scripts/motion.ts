/**
 * Site motion: smooth scroll (Lenis) + scroll-triggered reveals (GSAP).
 *
 * Both fully disabled under prefers-reduced-motion, per the mandatory rule in
 * both imported design skills (taste-skill 6.B, web-design-guidelines Animation).
 *
 * Reveals use IntersectionObserver to decide WHEN to animate, not GSAP
 * ScrollTrigger's scroll-position math. Tried ScrollTrigger first: it left
 * the hero heading permanently invisible (stuck at its gsap.from() opacity:0
 * state, confirmed directly, not a guess) because its scroll-position
 * calculations desync from Lenis's virtual scroll unless the two are wired
 * together carefully. This content is simple "items appear as they enter
 * viewport", no pinning or scrubbing, so IntersectionObserver is the more
 * robust tool for the job: it cannot desync from Lenis because it does not
 * read scroll position at all.
 */
import Lenis from "lenis";
import { gsap } from "gsap";

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (!prefersReducedMotion) {
  const lenis = new Lenis({
    duration: 1.0,
    easing: (t: number) => 1 - Math.pow(1 - t, 3),
  });

  function raf(time: number) {
    lenis.raf(time);
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);

  // Reveal targets: page content, excluding anything inside the React Demo
  // island (astro-island). GSAP writing inline styles to an unhydrated
  // island's DOM throws off React's hydration diff, confirmed directly via
  // a console hydration-mismatch error before this exclusion was added.
  const targets = Array.from(
    document.querySelectorAll<HTMLElement>(
      ".hero h1, .hero .dek, .hero .hero-figure, " +
        ".section h2, .section h3, .section p, .section .stat, .section .system-block, " +
        ".section .figure, .section .caveat, .section table, .section .method-list"
    )
  ).filter((el) => !el.closest("astro-island"));

  gsap.set(targets, { opacity: 0, y: 20 });

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        gsap.to(entry.target, { opacity: 1, y: 0, duration: 0.7, ease: "power2.out" });
        observer.unobserve(entry.target);
      }
    },
    { threshold: 0.15, rootMargin: "0px 0px -5% 0px" }
  );
  targets.forEach((el) => observer.observe(el));
}
