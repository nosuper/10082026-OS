// Naming the other seat inside a comment.
//
// frappe-ui ships a mention extension of its own and we do not use it.
// Its suggestion renderer only mounts the popup when the list already
// has entries at `onStart`, and @tiptap/suggestion v3 always starts
// empty - it fetches the items afterwards and delivers them to
// `onUpdate`. The popup is therefore built detached and never shown,
// which is a silent failure: the editor still highlights what you type
// and still inserts on Enter, with nothing on screen to pick from.
//
// So the node and the trigger are ours. The list itself is not drawn
// here: the extension hands its state to a callback and the thread
// renders it in its own DOM, which keeps it inside the card dialog
// rather than in a popup layer the dialog treats as "outside".
import { Extension, Node, mergeAttributes } from "@tiptap/core"
import { PluginKey } from "@tiptap/pm/state"
import Suggestion from "@tiptap/suggestion"

// The markup the server reads a mention out of (auraos/lib/comments.py)
// and the thread styles as one. Core Frappe reads the same shape when
// it notifies the named user, so this is a contract, not a detail.
export const MentionNode = Node.create({
  name: "mention",
  group: "inline",
  inline: true,
  atom: true,
  selectable: true,

  addAttributes() {
    return {
      id: {
        default: null,
        parseHTML: (el) => el.getAttribute("data-id"),
        renderHTML: (attrs) => (attrs.id ? { "data-id": attrs.id } : {}),
      },
      label: {
        default: null,
        parseHTML: (el) => el.getAttribute("data-label"),
        renderHTML: (attrs) => (attrs.label ? { "data-label": attrs.label } : {}),
      },
    }
  },

  parseHTML() {
    return [{ tag: 'span.mention[data-type="mention"]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "span",
      mergeAttributes(HTMLAttributes, { class: "mention", "data-type": "mention" }),
      `@${HTMLAttributes["data-label"] || HTMLAttributes["data-id"] || ""}`,
    ]
  },

  renderText({ node }) {
    return `@${node.attrs.label || node.attrs.id || ""}`
  },
})

/**
 * The @ trigger.
 *
 * `items(query)` returns [{id, label}] to offer. `render(state)` is
 * called with `{items, index, rect, command}` while the popup should be
 * open and with `null` when it should close; `command(item)` inserts
 * the mention. Arrow keys and Enter are handled here so the list the
 * thread draws stays in step with the caret.
 */
export function mentionSuggestion({ items, render }) {
  return Extension.create({
    name: "auraMentionSuggestion",

    addProseMirrorPlugins() {
      let open = null

      const publish = () => render(open && { ...open })

      const show = (props) => {
        open = {
          items: props.items || [],
          index: 0,
          command: props.command,
          rect: props.clientRect?.() || null,
        }
        publish()
      }

      const move = (step) => {
        const count = open.items.length
        open.index = (open.index + step + count) % count
        publish()
      }

      return [
        Suggestion({
          editor: this.editor,
          char: "@",
          pluginKey: new PluginKey("auraMentionSuggestion"),
          allowSpaces: false,
          decorationTag: "span",
          decorationClass: "mention-typing",
          items: ({ query }) => items(query),
          command: ({ editor, range, props }) => {
            editor
              .chain()
              .focus()
              .insertContentAt(range, [
                { type: "mention", attrs: { id: props.id, label: props.label } },
                { type: "text", text: " " },
              ])
              .run()
          },
          render: () => ({
            onStart: show,
            onUpdate: show,
            onKeyDown({ event }) {
              if (!open?.items.length) return false
              if (event.key === "ArrowDown") return move(1), true
              if (event.key === "ArrowUp") return move(-1), true
              if (event.key === "Enter" || event.key === "Tab") {
                open.command(open.items[open.index])
                return true
              }
              if (event.key === "Escape") {
                open = null
                publish()
                return true
              }
              return false
            },
            onExit() {
              open = null
              publish()
            },
          }),
        }),
      ]
    },
  })
}
