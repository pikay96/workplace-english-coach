import { useEffect, useId, useRef, type ReactNode } from "react";

export function Sheet({
  open,
  title,
  close,
  children,
}: {
  open: boolean;
  title: string;
  close: () => void;
  children: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal();
    if (!open && dialog.current?.open) dialog.current.close();
  }, [open]);
  return (
    <dialog
      className="detail-sheet"
      ref={dialog}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onClick={(event) => {
        if (event.target === dialog.current) close();
      }}
    >
      <div className="sheet-inner">
        <header className="sheet-header">
          <h2 id={titleId}>{title}</h2>
          <button
            autoFocus
            className="sheet-close"
            aria-label="Close details"
            onClick={close}
          >
            <img className="icon" src="/assets/icons/x.svg" alt="" />
          </button>
        </header>
        <div className="sheet-body">{children}</div>
      </div>
    </dialog>
  );
}
