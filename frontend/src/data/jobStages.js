// The agreed production flow, in board order. Must match the Job
// doctype's stage options and auraos.auraos.doctype.job.job.STAGES.
export const STAGES = [
  "Pre-production",
  "Shoot",
  "Post",
  "Feedback",
  "Delivery",
  "Nghiệm thu",
  "Chờ thanh toán",
  "Done",
]

// Rounds included before a revision becomes a change order — mirrors
// FREE_REVISION_ROUNDS on the server, which is the authority.
export const FREE_REVISION_ROUNDS = 2
