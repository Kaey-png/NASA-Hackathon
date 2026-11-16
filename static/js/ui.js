/* Gentle entrance animation. Skipped for people who prefer reduced motion. */
(function () {
  if (!window.gsap) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  gsap.from(".sheet", {
    y: 18, opacity: 0, duration: 0.5, ease: "power2.out", stagger: 0.08, clearProps: "all",
  });
})();
