'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';

/** One restrained entrance per marked element. Content is visible without JavaScript. */
export default function ScrollReveal() {
  const pathname = usePathname();

  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (preference.matches || !('IntersectionObserver' in window) || !Element.prototype.animate) return;

    const animations = new Set<Animation>();
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        observer.unobserve(entry.target);
        const animation = entry.target.animate(
          [{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'translateY(0)' }],
          { duration: 300, easing: 'cubic-bezier(0.2, 0.65, 0.3, 1)' },
        );
        animations.add(animation);
        void animation.finished.then(() => animations.delete(animation), () => animations.delete(animation));
      }
    }, { threshold: 0.12 });

    // Wait for the new route's DOM, including its client components, before observing.
    const frame = requestAnimationFrame(() => {
      document.querySelectorAll('[data-scroll-reveal]').forEach(element => observer.observe(element));
    });
    const stop = () => {
      if (!preference.matches) return;
      observer.disconnect();
      animations.forEach(animation => animation.cancel());
    };
    preference.addEventListener('change', stop);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      animations.forEach(animation => animation.cancel());
      preference.removeEventListener('change', stop);
    };
  }, [pathname]);

  return null;
}
