'use client';
import { useEffect, useRef, type ReactNode } from 'react';

export default function FittingDialog({ open, title, onClose, children, side = false }: {
  open: boolean; title: string; onClose: () => void; children: ReactNode; side?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    else if (!open && dialog.open) dialog.close();
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previous; };
  }, [open]);
  return <dialog ref={ref} className={`room-dialog ${side ? 'room-dialog-side' : ''}`} aria-label={title}
    onCancel={event => { event.preventDefault(); onClose(); }}
    onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="room-dialog-content">
      <div className="room-dialog-heading"><h2>{title}</h2><button type="button" className="room-close" aria-label={`Close ${title}`} onClick={onClose}>Close <span aria-hidden="true">×</span></button></div>
      {children}
    </div>
  </dialog>;
}
