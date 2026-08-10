// The money vocabulary the server owns — mirrors auraos.lib.settlement,
// which is the authority. The same words appear as Select options on
// Job Expense and Job Settlement, so a screen that spells one of them
// differently silently stops matching.

// Where an expense's money came from.
export const FROM_ADVANCE = "Advance"
export const FROM_COMPANY = "Company"

// Which way a float has to move to close.
export const RETURN = "Return"
export const TOP_UP = "Top-up"
export const EVEN = "Even"

// Where an expense lands when it names no category the quote knows.
export const UNCATEGORISED = "Uncategorised"
