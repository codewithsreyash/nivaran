import { useCallback, useEffect, useRef, useState, type RefObject } from 'react';
import { Bell, CheckCheck, Menu, RefreshCw, X } from 'lucide-react';
import { notificationsAPI } from '../lib/api';
import type { Notification } from '../types';
import { formatDateTime } from '../lib/utils';

interface TopbarProps {
  onMenuClick: () => void;
  menuButtonRef: RefObject<HTMLButtonElement | null>;
  isMenuOpen: boolean;
}

export default function Topbar({ onMenuClick, menuButtonRef, isMenuOpen }: TopbarProps) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showNotifs, setShowNotifs] = useState(false);
  const [notificationError, setNotificationError] = useState(false);
  const [notificationActionError, setNotificationActionError] = useState(false);
  const [loadingNotifications, setLoadingNotifications] = useState(true);
  const notificationRef = useRef<HTMLDivElement>(null);
  const unread = notifications.filter((n) => !n.is_read).length;

  const loadNotifications = useCallback(async (signal?: AbortSignal) => {
    setLoadingNotifications(true);
    setNotificationError(false);
    try {
      const response = await notificationsAPI.list({ unread_only: false }, signal);
      if (!signal?.aborted) setNotifications(response.data.slice(0, 10));
    } catch {
      if (!signal?.aborted) setNotificationError(true);
    } finally {
      if (!signal?.aborted) setLoadingNotifications(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void loadNotifications(controller.signal);
    return () => controller.abort();
  }, [loadNotifications]);

  useEffect(() => {
    if (!showNotifs) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!notificationRef.current?.contains(event.target as Node)) setShowNotifs(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setShowNotifs(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [showNotifs]);

  const markRead = async (id: number) => {
    setNotificationActionError(false);
    try {
      await notificationsAPI.markRead(id);
      setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, is_read: true } : n));
    } catch { setNotificationActionError(true); }
  };

  const markAllRead = async () => {
    const unreadIds = notifications.filter((n) => !n.is_read).map((n) => n.id);
    setNotificationActionError(false);
    const results = await Promise.allSettled(unreadIds.map((id) => notificationsAPI.markRead(id)));
    const succeeded = new Set(unreadIds.filter((_id, index) => results[index].status === 'fulfilled'));
    setNotifications((prev) => prev.map((n) => succeeded.has(n.id) ? { ...n, is_read: true } : n));
    setNotificationActionError(results.some((result) => result.status === 'rejected'));
  };

  const typeColor: Record<string, string> = {
    overdue: 'text-status-danger',
    overlap: 'text-status-info',
    deadline: 'text-status-warning',
  };
  const typeIcon: Record<string, string> = { overdue: '!', overlap: '↔', deadline: '◷' };

  return (
    <header className="app-topbar">
      <button ref={menuButtonRef} onClick={onMenuClick} className="icon-button mobile-menu-button"
        aria-label="Open navigation menu" aria-controls="primary-navigation" aria-expanded={isMenuOpen}>
        <Menu size={21} />
      </button>
      <div className="topbar-context">
        <span className="topbar-product">AICTE OneView</span>
        <span className="topbar-divider" aria-hidden="true">/</span>
        <span className="topbar-caption">Complaint Intelligence Platform</span>
      </div>
      <div className="topbar-spacer" />
      <span className="environment-badge"><span aria-hidden="true" />Demonstration environment</span>

      <div className="notification-anchor" ref={notificationRef}>
        <button onClick={() => setShowNotifs((shown) => !shown)} className="icon-button notification-trigger"
          aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`} aria-haspopup="dialog" aria-expanded={showNotifs}>
          <Bell size={19} aria-hidden="true" />
          {unread > 0 && <span className="notification-count" aria-label={`${unread} unread`}>
            {unread > 9 ? '9+' : unread}
          </span>}
        </button>

        {showNotifs && <section className="notification-panel" role="dialog" aria-label="Notifications">
          <div className="notification-heading">
            <h2>Notifications{unread > 0 ? <span className="notification-total">{unread}</span> : null}</h2>
            <div className="notification-actions">
              {unread > 0 && <button onClick={markAllRead} className="text-action" aria-label="Mark all notifications as read">
                <CheckCheck size={15} /><span>Mark all read</span>
              </button>}
              <button onClick={() => setShowNotifs(false)} className="icon-button compact-icon-button" aria-label="Close notifications">
                <X size={17} />
              </button>
            </div>
          </div>
          <div className="notification-list">
            {notificationError ? <div className="notification-empty" role="status">Notifications could not be loaded.<button className="text-action notification-retry" onClick={() => void loadNotifications()}><RefreshCw size={13} />Retry</button></div>
              : loadingNotifications ? <p className="notification-empty" role="status">Loading notifications…</p>
                : notifications.length === 0 ? <p className="notification-empty">No notifications</p> : notifications.slice(0, 5).map((notification) => (
              <button key={notification.id} onClick={() => markRead(notification.id)}
                className={`notification-item ${!notification.is_read ? 'is-unread' : ''}`}>
                <span className={`notification-type ${typeColor[notification.notification_type] ?? 'text-slate-500'}`} aria-hidden="true">
                  {typeIcon[notification.notification_type] ?? 'i'}
                </span>
                <span className="notification-copy">
                  <span className="notification-title">{notification.title}</span>
                  <span className="notification-message">{notification.message}</span>
                  <span className="notification-date">{formatDateTime(notification.created_at)}</span>
                </span>
                {!notification.is_read && <span className="unread-indicator" aria-label="Unread" />}
              </button>
            ))}
            {notificationActionError && <p className="notification-empty notification-action-error" role="alert">Could not update one or more notifications. Please retry.</p>}
          </div>
        </section>}
      </div>
    </header>
  );
}
