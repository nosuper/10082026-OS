// The one rich-text toolbar this app has, and a small editor built on it.
//
// There is deliberately no second editor. The template writer in
// paperwork.tsx had the only formatting controls in aura-next - bold, italic,
// a bulleted list and a block format - over a `contentEditable`, and issue
// #120 wanted the same controls on the deal brief. Copying them would have
// left two toolbars to keep in step; #66 will put a third surface on this, so
// the copy would have had to be made twice.
//
// **Why not TipTap.** #120 asked for the TipTap toolbar to be reused, but
// TipTap is not in this app: it lives in the frozen Vue frontend, through
// frappe-ui's TextEditor. Pulling it into React to satisfy the letter of that
// constraint would create the exact second editor the constraint exists to
// prevent, and would add a dependency to a screen that needs four buttons.
//
// **Why execCommand, which is deprecated.** It is what the template writer
// already uses, every browser this app runs in still implements it, and the
// alternative is the editor framework the paragraph above declines. If it
// ever goes, it goes from one file.
//
// **What the controls may emit is not a free choice.** Anything typed here
// lands in a Frappe `Text Editor` field, which Frappe runs through
// `sanitize_html` on save. `p`, `b`, `i`, `h1`-`h3`, `ul` and `li` survive it
// intact - checked against the running site, not assumed - and a `<script>` is
// neutralised. A control whose markup the sanitiser dropped would be a button
// that silently does nothing.

import { Bold, Italic, List } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

/** One toolbar button. `onMouseDown` rather than `onClick`, and prevented, so
 *  pressing it never takes the selection out of the editor first. */
export function ToolButton({
  label,
  onPress,
  children,
}: {
  label: string;
  onPress: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onMouseDown={(event) => {
        event.preventDefault();
        onPress();
      }}
      className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
    >
      {children}
    </button>
  );
}

/**
 * Bold, italic, bulleted list and a block format, acting on whatever
 * `contentEditable` currently holds the selection.
 *
 * It takes no editor reference on purpose: `execCommand` works on the
 * document's selection, and the buttons never steal it. That is what lets the
 * template writer keep its own body, with its placeholder machinery attached,
 * while sharing this row.
 *
 * `extras` is for controls that only make sense on one surface - the template
 * writer's field inserter, say - so they sit in the same row rather than in a
 * second bar underneath it.
 */
export function EditorToolbar({ extras }: { extras?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-1 rounded-t-lg border border-border bg-secondary/60 px-2 py-1.5">
      <ToolButton label="Bold" onPress={() => document.execCommand("bold")}>
        <Bold className="size-3.5" />
      </ToolButton>
      <ToolButton label="Italic" onPress={() => document.execCommand("italic")}>
        <Italic className="size-3.5" />
      </ToolButton>
      <ToolButton label="Bulleted list" onPress={() => document.execCommand("insertUnorderedList")}>
        <List className="size-3.5" />
      </ToolButton>
      <span className="mx-1 h-4 w-px bg-border" />
      <select
        defaultValue="p"
        aria-label="Text style"
        onMouseDown={(event) => event.stopPropagation()}
        onChange={(event) => {
          document.execCommand("formatBlock", false, event.target.value);
          event.target.value = "p";
        }}
        className="rounded-md border border-border bg-background px-2 py-1 text-xs"
      >
        <option value="p">Body text</option>
        <option value="h1">Heading 1</option>
        <option value="h2">Heading 2</option>
        <option value="h3">Heading 3</option>
      </select>
      {extras}
    </div>
  );
}

/**
 * A small rich-text field: the toolbar above, an editable body below.
 *
 * **Uncontrolled by design.** The body's HTML is written once, from
 * `defaultValue`, and never again while the user types - a `contentEditable`
 * re-rendered from state on every keystroke puts the caret back at the start
 * of the line, which is the classic way this component is got wrong. `onChange`
 * reports outwards; nothing writes back in.
 *
 * To load a different record into it, change the React `key`. Remounting is
 * the honest way to say "this is a different document now", and it is what the
 * caller already knows: they are the ones who fetched it.
 */
export function RichText({
  defaultValue,
  onChange,
  placeholder,
  ariaLabel,
  className = "min-h-[7rem]",
}: {
  defaultValue: string;
  onChange: (html: string) => void;
  placeholder?: string | undefined;
  ariaLabel?: string | undefined;
  className?: string | undefined;
}) {
  const body = useRef<HTMLDivElement>(null);

  // Once, on mount. An empty paragraph rather than nothing, so the caret has a
  // block to sit in and the first thing typed is a paragraph like every other.
  useEffect(() => {
    if (body.current) body.current.innerHTML = defaultValue || "<p><br></p>";
    // defaultValue is deliberately not a dependency: see the docblock.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <EditorToolbar />
      <div
        ref={body}
        contentEditable
        suppressContentEditableWarning
        role="textbox"
        aria-multiline="true"
        aria-label={ariaLabel}
        data-placeholder={placeholder}
        onInput={(event) => onChange(event.currentTarget.innerHTML)}
        className={`aura-rich overflow-y-auto rounded-b-lg border border-t-0 border-border bg-background px-3 py-2 text-sm outline-none focus:border-border-strong ${className}`}
      />
    </div>
  );
}
