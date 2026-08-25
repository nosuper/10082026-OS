// The managed lists on Settings: deal sources, project types, crafts (#29,
// ported at #165).
//
// One read, `auraos.api.get_vocabularies`, and every write returns the whole
// set again — so a rename that moved forty deals and a removal that was
// refused both land as one fresh, complete answer rather than as a patch this
// file would have to apply. Nothing here recomputes a use count.
//
// **Settings is no longer a founder-only door, and this is why.** A producer
// manages deal sources; the margin floor on the same page stays out of reach.
// So this card renders for anyone who may read a deal, and `can_manage` — per
// list, decided by the server — is what turns the editing on. A producer sees
// the sources section editable and the project-type section read-only, which
// is one screen telling the truth rather than two screens.
//
// **Every refusal here is the server's, printed as sent.** A value in use
// cannot be removed and the message names how many records hold it; a rename
// carries every deal across. Both rules live in `auraos.lib.vocabulary`, and a
// browser that guessed at them would guess wrong the first time somebody added
// a fourth list.

import { useState } from "react";
import { Check, Pencil, Plus, X } from "lucide-react";

import { Card, Pill, inputClass } from "@/components/aura/primitives";
import { ErrorState, QueryState } from "@/components/aura/states";
import { countLabel } from "@/lib/format";
import { resultOf, useMethod, useMethodMutation } from "@/lib/queries";
import { cn } from "@/lib/utils";

/** Pinned by auraos/tests/test_vocabulary_api.py. */
type VocabularyValue = {
  name: string;
  /** How many records hold this value. Counted by the server, never here. */
  in_use: number;
};

type Vocabulary = {
  key: string;
  label: string;
  /** Whether this session may edit this particular list. Per list, not per user. */
  can_manage: boolean;
  values: VocabularyValue[];
};

const VOCABULARIES = resultOf("auraos.api.get_vocabularies");

export function VocabularyLists() {
  const lists = useMethod<Vocabulary[]>("auraos.api.get_vocabularies");
  const vocabularies = lists.data ?? [];

  return (
    <Card
      title="Managed lists"
      subtitle="The vocabularies a deal picks from. Renaming one carries every record on it across."
    >
      <QueryState
        query={lists}
        loadingRows={3}
        isEmpty={() => vocabularies.length === 0}
        empty={{ title: "No managed lists.", detail: "Nothing on this site is editable here." }}
      >
        {() => (
          <div className="grid gap-4 p-4 md:grid-cols-2 xl:grid-cols-3">
            {vocabularies.map((vocab) => (
              <VocabularySection key={vocab.key} vocab={vocab} />
            ))}
          </div>
        )}
      </QueryState>
    </Card>
  );
}

function VocabularySection({ vocab }: { vocab: Vocabulary }) {
  const [adding, setAdding] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [renamed, setRenamed] = useState("");

  const invalidate = [VOCABULARIES];
  const add = useMethodMutation<unknown, Record<string, unknown>>(
    "auraos.api.add_vocabulary_value",
    { invalidate, onSuccess: () => setAdding("") },
  );
  const rename = useMethodMutation<unknown, Record<string, unknown>>(
    "auraos.api.rename_vocabulary_value",
    { invalidate, onSuccess: () => setEditing(null) },
  );
  const remove = useMethodMutation<unknown, Record<string, unknown>>(
    "auraos.api.remove_vocabulary_value",
    { invalidate },
  );

  const error = add.error || rename.error || remove.error;
  const busy = add.isPending || rename.isPending || remove.isPending;

  return (
    <div className="rounded-xl border border-border p-3">
      <div className="flex items-baseline justify-between gap-2">
        <span className="label-caps">{vocab.label}</span>
        {vocab.can_manage ? null : <Pill tone="outline">read only</Pill>}
      </div>

      <ul className="mt-2 divide-y divide-border">
        {vocab.values.map((value) => (
          <li key={value.name} className="flex items-center gap-1.5 py-1.5">
            {editing === value.name ? (
              <>
                <input
                  aria-label={`Rename ${value.name}`}
                  value={renamed}
                  autoFocus
                  onChange={(e) => setRenamed(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && renamed.trim()) {
                      rename.mutate({
                        kind: vocab.key,
                        value: value.name,
                        new_value: renamed.trim(),
                      });
                    }
                    if (e.key === "Escape") setEditing(null);
                  }}
                  className={cn(inputClass, "py-1 text-xs")}
                />
                <button
                  type="button"
                  aria-label="Save name"
                  disabled={!renamed.trim() || busy}
                  onClick={() =>
                    rename.mutate({
                      kind: vocab.key,
                      value: value.name,
                      new_value: renamed.trim(),
                    })
                  }
                  className="rounded-md border border-border p-1 hover:bg-secondary disabled:opacity-50"
                >
                  <Check className="size-3" strokeWidth={2} />
                </button>
                <button
                  type="button"
                  aria-label="Cancel rename"
                  onClick={() => setEditing(null)}
                  className="rounded-md border border-border p-1 hover:bg-secondary"
                >
                  <X className="size-3" strokeWidth={2} />
                </button>
              </>
            ) : (
              <>
                <span className="min-w-0 flex-1 truncate text-sm">{value.name}</span>
                {/* The count is what makes a refusal readable before it
                    happens: a value on eleven deals is visibly not removable. */}
                {value.in_use > 0 ? (
                  <span className="label-caps shrink-0">{value.in_use}</span>
                ) : null}
                {vocab.can_manage ? (
                  <>
                    <button
                      type="button"
                      aria-label={`Rename ${value.name}`}
                      onClick={() => {
                        setEditing(value.name);
                        setRenamed(value.name);
                      }}
                      className="rounded-md border border-border p-1 text-muted-foreground hover:bg-secondary hover:text-foreground"
                    >
                      <Pencil className="size-3" strokeWidth={1.75} />
                    </button>
                    <button
                      type="button"
                      aria-label={`Remove ${value.name}`}
                      disabled={busy}
                      onClick={() => remove.mutate({ kind: vocab.key, value: value.name })}
                      className="rounded-md border border-border p-1 text-muted-foreground hover:bg-secondary hover:text-ember disabled:opacity-50"
                    >
                      <X className="size-3" strokeWidth={1.75} />
                    </button>
                  </>
                ) : null}
              </>
            )}
          </li>
        ))}
        {vocab.values.length === 0 ? (
          <li className="py-1.5 text-xs text-muted-foreground">Nothing in this list yet.</li>
        ) : null}
      </ul>

      {vocab.can_manage ? (
        <div className="mt-2 flex items-center gap-1.5">
          <input
            aria-label={`Add to ${vocab.label.toLowerCase()}`}
            placeholder={`Add to ${vocab.label.toLowerCase()}`}
            value={adding}
            onChange={(e) => setAdding(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && adding.trim()) {
                add.mutate({ kind: vocab.key, value: adding.trim() });
              }
            }}
            className={cn(inputClass, "py-1 text-xs")}
          />
          <button
            type="button"
            aria-label={`Add to ${vocab.label}`}
            disabled={!adding.trim() || busy}
            onClick={() => add.mutate({ kind: vocab.key, value: adding.trim() })}
            className="rounded-md bg-primary p-1.5 text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            <Plus className="size-3" strokeWidth={2} />
          </button>
        </div>
      ) : null}

      {vocab.can_manage && vocab.values.some((v) => v.in_use > 0) ? (
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
          A value {countLabel(1, "record")} still holds cannot be removed — renaming it carries
          those records across instead.
        </p>
      ) : null}

      {/* The server's own words. A removal refused because eleven deals hold
          the value says so, with the number, and this file does not rewrite
          it into something vaguer. */}
      {error ? <ErrorState error={error} /> : null}
    </div>
  );
}
