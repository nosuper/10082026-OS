// The agreed pipeline, in board order (spec issue #2, story 3).
// One color per stage, used everywhere a stage appears - board column
// dots, table pills and page chips must never disagree.
export const STAGES = [
  {
    label: "Brief Received",
    value: "Brief Received",
    dot: "bg-gray-400",
    pill: "bg-gray-100 text-gray-700",
  },
  {
    label: "De-brief",
    value: "De-brief",
    // blue, not sky: frappe-ui's Tailwind palette has no sky (nor
    // emerald, indigo, lime) - an off-palette class silently renders
    // transparent.
    dot: "bg-blue-500",
    pill: "bg-blue-50 text-blue-700",
  },
  {
    label: "Breakdown",
    value: "Breakdown",
    dot: "bg-violet-500",
    pill: "bg-violet-50 text-violet-700",
  },
  {
    label: "Quote Sent",
    value: "Quote Sent",
    dot: "bg-amber-500",
    pill: "bg-amber-50 text-amber-800",
  },
  {
    label: "Negotiation",
    value: "Negotiation",
    dot: "bg-orange-500",
    pill: "bg-orange-50 text-orange-800",
  },
  {
    label: "Won",
    value: "Won",
    dot: "bg-green-500",
    pill: "bg-green-50 text-green-700",
  },
  {
    label: "Lost",
    value: "Lost",
    dot: "bg-red-500",
    pill: "bg-red-50 text-red-700",
  },
]

export function stageClass(stage) {
  return (
    STAGES.find((entry) => entry.value === stage)?.pill ||
    "bg-gray-100 text-gray-700"
  )
}

// The production flow's colors (A4). Names must match
// data/jobStages.js STAGES - the flow itself lives there; this is only
// how each stage looks, with a gray fallback for anything unmapped.
// Palette note: frappe-ui's Tailwind preset ships amber, blue, cyan,
// gray, green, orange, pink, red, teal, violet, yellow - nothing else.
const JOB_STAGE_DOTS = {
  "Pre-production": "bg-cyan-500",
  "Production": "bg-blue-500",
  "Post-production": "bg-violet-500",
  "Client review": "bg-amber-500",
  "Delivery": "bg-teal-500",
  "Client sign-off": "bg-yellow-500",
  "Awaiting payment": "bg-orange-500",
  "Complete": "bg-green-500",
}

export function jobStageDot(stage) {
  return JOB_STAGE_DOTS[stage] || "bg-gray-400"
}
