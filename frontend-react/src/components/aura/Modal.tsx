// The one dialog shell this app has.
//
// It was written inside the paperwork screen, for the window that opens a
// template or a generated paper. #66 gave it a second caller - the Library
// opens a document the same way - so it moved here rather than being copied,
// on the same reasoning that put the rich-text toolbar in RichText.tsx: a
// copied dialog is two sets of escape handling and two answers about what a
// backdrop click does.
//
// Deliberately not a component library. Escape closes, the backdrop closes,
// the header carries a title and the footer carries whatever the caller
// needs. Anything more specific belongs to the caller.

import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";

export const DIALOG_BUTTON =
  "rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary";

export function Modal({
  title,
  onClose,
  children,
  footer,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer: ReactNode;
}) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:p-8">
      <button
        type="button"
        aria-label="Close"
        onClick={onClose}
        className="fixed inset-0 bg-primary/25 backdrop-blur-[1px]"
      />
      <div
        role="dialog"
        aria-label={title}
        className="relative z-10 w-full max-w-4xl rounded-xl border border-border bg-card shadow-lg"
      >
        <header className="flex items-start gap-3 border-b border-border px-5 py-4">
          <h2 className="min-w-0 flex-1 truncate font-display text-base font-semibold tracking-tight">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary"
          >
            <X className="size-4" />
          </button>
        </header>
        <div className="px-5 py-5">{children}</div>
        <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-border px-5 py-4">
          {footer}
        </footer>
      </div>
    </div>
  );
}
