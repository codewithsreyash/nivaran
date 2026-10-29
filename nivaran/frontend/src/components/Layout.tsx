import { useCallback, useEffect, useRef, useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

export default function Layout() {
  const [isMobile, setIsMobile] = useState(() => window.matchMedia('(max-width: 767px)').matches);
  const [mobileOpen, setMobileOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 767px)');
    const onChange = (event: MediaQueryListEvent) => {
      setIsMobile(event.matches);
      setMobileOpen(false);
    };
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, []);

  const closeNavigation = useCallback(() => {
    setMobileOpen(false);
    if (isMobile) window.requestAnimationFrame(() => menuButtonRef.current?.focus());
  }, [isMobile]);

  useEffect(() => {
    if (!mobileOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeNavigation();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [mobileOpen, closeNavigation]);

  return (
    <div className="app-shell">
      <Sidebar isMobile={isMobile} mobileOpen={mobileOpen} onClose={closeNavigation} />
      <div className="app-workspace">
        <Topbar onMenuClick={() => setMobileOpen(true)} menuButtonRef={menuButtonRef} isMenuOpen={mobileOpen} />
        <main className="app-main">
          <div className="app-content"><Outlet /></div>
        </main>
      </div>
    </div>
  );
}
