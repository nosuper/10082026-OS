# Quote previews freeze on client exposure

A deal has at most one mutable quote preview, which automatically follows each successful save of its client-facing source data. Marking it Sent or receiving its first guest open — whichever comes first — atomically freezes all client-visible content, including branding and PDF output, into the next quote version; authenticated internal opens do not freeze it.

This keeps typo fixes painless before delivery without allowing a page to change after a client could have seen it. Freezing only on an explicit Sent action was rejected because a producer can share the link and forget to mark it; allowing edits after exposure was rejected because the open log would no longer identify what the client saw.

After a version freezes, later breakdown changes do not alter it or automatically create a public link. The producer explicitly publishes the next preview at a new token, and only frozen quote versions form the version history.
