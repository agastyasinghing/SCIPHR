import { useEffect, useRef, useState } from 'react';

/**
 * useScrollAnimation Hook
 * Detects when an element enters the viewport and triggers animation
 * 
 * @param {number} threshold - Percentage of element visibility to trigger (0-1)
 * @returns {[ref, isVisible]} - Ref to attach to element and visibility state
 */
export const useScrollAnimation = (threshold = 0.1) => {
  const ref = useRef(null);
  const [isVisible, setIsVisible] = useState(false);
  
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          // Once visible, keep it visible
          observer.unobserve(entry.target);
        }
      },
      {
        threshold,
        rootMargin: '0px 0px -100px 0px', // Trigger slightly before element is in view
      }
    );
    
    if (ref.current) {
      observer.observe(ref.current);
    }
    
    return () => {
      if (ref.current) {
        observer.unobserve(ref.current);
      }
    };
  }, [threshold]);
  
  return [ref, isVisible];
};

export default useScrollAnimation;