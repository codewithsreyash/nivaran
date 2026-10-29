import { useEffect, useRef, useState } from 'react';

interface Props {
  value: number;
  label: string;
  prefix?: string;
  suffix?: string;
  duration?: number; // ms, default 1200
}

export default function AnimatedStat({
  value,
  label,
  prefix = '',
  suffix = '',
  duration = 1200,
}: Props) {
  const [display, setDisplay] = useState(0);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    const start = performance.now();
    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(eased * value));
      if (progress < 1) raf.current = requestAnimationFrame(animate);
    };
    raf.current = requestAnimationFrame(animate);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [value, duration]);

  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-3xl font-bold text-slate-100 tabular-nums">
        {prefix}{display.toLocaleString()}{suffix}
      </span>
      <span className="text-xs text-slate-500 font-medium uppercase tracking-wide">{label}</span>
    </div>
  );
}
