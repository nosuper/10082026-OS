// The agreed production flow, in board order. Must match the Job
// doctype's stage options and auraos.auraos.doctype.job.job.STAGES.
export const STAGES = [
  "Pre-production",
  "Production",
  "Post-production",
  "Client review",
  "Delivery",
  "Client sign-off",
  "Awaiting payment",
  "Complete",
]

// Rounds included before a revision becomes a change order - mirrors
// INCLUDED_REVISION_ROUNDS on the server, which is the authority.
export const INCLUDED_REVISION_ROUNDS = 2

// Where logging a revision sends a job that has already been shown to
// the client, and the last stage that still redoes - mirrors
// REDO_STAGE and LAST_REDOABLE_STAGE on the server.
export const REDO_STAGE = "Post-production"
export const LAST_REDOABLE_STAGE = "Delivery"
