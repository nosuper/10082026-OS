// What a numbered contract needs before it can be generated (#139).
//
// Five values live on no record: when the contract was signed, how many
// days each half of the payment is due in, and the service window. They
// are asked for here rather than stored on the Job, because storing them
// would claim the job knows something it does not - and #139 says a
// field is added when the founder wants the history, not as a side
// effect of needing a value once.
//
// The number is proposed by the server and shown before anything is
// written. Editable, because the founder sometimes has to match a number
// a client already has on file; frozen the moment the paper exists.

import { useEffect, useState } from "react";

import { DIALOG_BUTTON, Modal } from "@/components/aura/Modal";
import { ErrorState } from "@/components/aura/states";
import { useMethodMutation } from "@/lib/queries";

export type ContractTerms = {
  signed_on: string;
  deposit_days: string;
  final_days: string;
  service_start: string;
  service_end: string;
};

export type Proposal = {
  kind: string;
  number: string | null;
  /** What is missing, when the server could not propose a number. */
  needs: "short_code" | "contract" | null;
};

const EMPTY: ContractTerms = {
  signed_on: "",
  deposit_days: "",
  final_days: "",
  service_start: "",
  service_end: "",
};

const INPUT =
  "w-full rounded-lg border border-border bg-background px-2 py-1 text-sm outline-none focus:border-border-strong";

/** Why a number could not be proposed, in the words of its fix.
 *
 *  Both cases have a person as the remedy and neither has a sensible
 *  default, so the dialog says who has to do what rather than showing a
 *  blank field the founder has to interpret. */
function absence(needs: Proposal["needs"]) {
  if (needs === "short_code")
    return "This client has no short code yet, and the number is built from it. Add one in Contacts, or type the number below.";
  if (needs === "contract")
    return "No contract has been generated for this job yet, and this paper takes its number from one. Generate the contract first, or type the number below.";
  return null;
}

export function ContractDetails({
  job,
  template,
  kind,
  onCancel,
  onConfirm,
}: {
  job: string;
  template: string;
  kind: string;
  onCancel: () => void;
  onConfirm: (number: string | null, terms: ContractTerms) => void;
}) {
  const [terms, setTerms] = useState<ContractTerms>(EMPTY);
  const [number, setNumber] = useState("");
  const [proposal, setProposal] = useState<Proposal | null>(null);

  const proposer = useMethodMutation<Proposal, Record<string, unknown>>(
    "auraos.api.propose_contract_number",
    {
      onSuccess: (result) => {
        setProposal(result);
        // Only ever fills a field the founder has not typed into. A
        // proposal arriving after an edit must not overwrite it.
        setNumber((current) => current || result?.number || "");
      },
    },
  );

  // The number depends on the signing date, so it is re-proposed when
  // that changes and not before: asking on every keystroke of a day
  // count would be a request per character for a value it ignores.
  useEffect(() => {
    if (!terms.signed_on) return;
    proposer.mutate({ job, template, signed_on: terms.signed_on });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job, template, terms.signed_on]);

  const field = (key: keyof ContractTerms) => ({
    value: terms[key],
    onChange: (event: React.ChangeEvent<HTMLInputElement>) =>
      setTerms((current) => ({ ...current, [key]: event.target.value })),
    className: INPUT,
  });

  const note = absence(proposal?.needs ?? null);

  return (
    <Modal
      title={`${kind} details`}
      onClose={onCancel}
      footer={
        <>
          <button type="button" className={DIALOG_BUTTON} onClick={onCancel}>
            Cancel
          </button>
          <button
            type="button"
            className={DIALOG_BUTTON}
            disabled={!terms.signed_on}
            onClick={() => onConfirm(number.trim() || null, terms)}
          >
            Continue
          </button>
        </>
      }
    >
      <div className="space-y-3">
        <div>
          <div className="label-caps">Signing date</div>
          <input type="date" {...field("signed_on")} />
          <p className="mt-1 text-[11px] text-muted-foreground">
            The date the contract is agreed, which is what the number is built from. Not the date it
            is generated: regenerating this paper next week must not rename the agreement.
          </p>
        </div>

        <div>
          <div className="label-caps">Contract number</div>
          <input
            value={number}
            onChange={(event) => setNumber(event.target.value)}
            className={INPUT}
            placeholder={terms.signed_on ? "" : "Pick a signing date first"}
          />
          {note ? <p className="mt-1 text-[11px] text-ember">{note}</p> : null}
          <p className="mt-1 text-[11px] text-muted-foreground">
            Fixed on the paper once it is generated, and never re-derived afterwards.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="label-caps">Deposit due in (days)</div>
            <input inputMode="numeric" {...field("deposit_days")} />
          </div>
          <div>
            <div className="label-caps">Final due in (days)</div>
            <input inputMode="numeric" {...field("final_days")} />
          </div>
          <div>
            <div className="label-caps">Service starts</div>
            <input type="date" {...field("service_start")} />
          </div>
          <div>
            <div className="label-caps">Service ends</div>
            <input type="date" {...field("service_end")} />
          </div>
        </div>

        <ErrorState error={proposer.error} />
      </div>
    </Modal>
  );
}
