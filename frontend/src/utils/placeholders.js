// Placeholders live as {{client.tax_code}} in a template's stored
// source — the fill pipeline's contract. In the editor they appear as
// mention chips (the Google-Docs smart-chip pattern): readable, atomic,
// deletable in one keystroke, and offered by typing @. These two
// convert between the forms, so neither side knows about the other.

const PLACEHOLDER = /\{\{\s*([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)\s*\}\}/g

// Matches the mention span frappe-ui's TextEditor renders. Attribute
// order is not guaranteed, so data-id is pulled from wherever it sits.
const MENTION = /<span[^>]*data-type="mention"[^>]*>.*?<\/span>/g
const DATA_ID = /data-id="([^"]+)"/

export function sourceToEditor(source) {
  return source.replace(
    PLACEHOLDER,
    (match, name) =>
      `<span class="mention" data-type="mention" data-id="${name}" ` +
      `data-label="${name}">@${name}</span>`
  )
}

export function editorToSource(html) {
  return html.replace(MENTION, (span) => {
    const id = span.match(DATA_ID)?.[1]
    return id ? `{{${id}}}` : ""
  })
}
