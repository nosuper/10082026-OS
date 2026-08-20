// The settled figures an acceptance document states (#153).
//
// The founder's own instruction is the design: "cứ để tôi chỉnh sửa
// phần nghiệm thu này nếu có thay đổi phát sinh hoặc khấu trừ, rồi nhập
// lại số là xong - không cần automation những phần này". So this asks
// for three numbers and computes nothing it was not given.
//
// Pre-filled from the contract, because settling at the contracted value
// is the normal case. Typing over a field is how a change is recorded,
// and the typing IS the review - there is no confirmation step, because
// a checkbox acknowledging numbers somebody just typed adds a click and
// no information.
//
// What is computed here is only arithmetic BETWEEN the numbers: the
// difference against the contract and what remains after collections.
// That is the safe kind - it removes hand-math from a page somebody
// signs without inventing any figure the founder did not state.

import { useEffect, useState } from "react";

import { DIALOG_BUTTON, Modal } from "@/components/aura/Modal";
import { ErrorState } from "@/components/aura/states";
import { vnd } from "@/lib/format";
import { resultOf, useMethod } from "@/lib/queries";

/** The three rows the document states, in its own order. */
const BANDS = [
  { key: "pre_vat", label: "Hợp đồng (chưa VAT)" },
  { key: "vat", label: "Thuế GTGT" },
  { key: "total", label: "Tổng cộng" },
] as const;

type Band = (typeof BANDS)[number]["key"];
type Figures = Record<Band, string>;

type Prefill = {
  contracted: Record<Band, number | null>;
  collected: Record<Band, number | null>;
  refusals: string[];
};

const EMPTY: Figures = { pre_vat: "", vat: "", total: "" };

const INPUT =
  "w-full rounded-lg border border-border bg-background px-2 py-1 text-right text-sm outline-none focus:border-border-strong";

/** A typed figure as a number, or null when it is not one.
 *
 *  Blank is null rather than zero: an empty settled field means the
 *  founder has not said, and a zero would say the work was settled at
 *  nothing. The server draws the same distinction. */
function figure(text: string): number | null {
  const cleaned = text.replace(/[^\d-]/g, "");
  if (!cleaned) return null;
  const value = Number(cleaned);
  return Number.isFinite(value) ? value : null;
}

/** Shown beside each row so the founder sees the consequence of the
 *  number they just typed, before the document exists rather than after
 *  it is signed. Absent stays absent - a missing figure shows a dash,
 *  never a zero. */
function derived(settled: number | null, contracted: number | null, collected: number | null) {
  return {
    difference: settled !== null && contracted !== null ? settled - contracted : null,
    remaining: settled !== null && collected !== null ? settled - collected : null,
  };
}

function Cell({ value }: { value: number | null }) {
  if (value === null) return <span className="text-muted-foreground">—</span>;
  return <span className={value < 0 ? "text-ember" : undefined}>{vnd(value)}</span>;
}

export function AcceptanceFigures({
  job,
  onCancel,
  onConfirm,
}: {
  job: string;
  onCancel: () => void;
  onConfirm: (settled: Record<string, number | null>) => void;
}) {
  const prefill = useMethod<Prefill>("auraos.api.job_acceptance_figures", { job });
  const [figures, setFigures] = useState<Figures>(EMPTY);
  const [touched, setTouched] = useState(false);

  // Filled once, when the contract's figures arrive. Not on every
  // render: overwriting what somebody is typing because a refetch
  // landed is the clobber this codebase has now met three times.
  useEffect(() => {
    if (touched || !prefill.data) return;
    const { contracted } = prefill.data;
    setFigures({
      pre_vat: contracted.pre_vat === null ? "" : String(contracted.pre_vat),
      vat: contracted.vat === null ? "" : String(contracted.vat),
      total: contracted.total === null ? "" : String(contracted.total),
    });
  }, [prefill.data, touched]);

  const contracted = prefill.data?.contracted;
  const collected = prefill.data?.collected;

  return (
    <Modal
      title="Nghiệm thu - giá trị thanh lý"
      onClose={onCancel}
      footer={
        <>
          <button type="button" className={DIALOG_BUTTON} onClick={onCancel}>
            Cancel
          </button>
          <button
            type="button"
            className={DIALOG_BUTTON}
            onClick={() =>
              onConfirm({
                pre_vat: figure(figures.pre_vat),
                vat: figure(figures.vat),
                total: figure(figures.total),
              })
            }
          >
            Continue
          </button>
        </>
      }
    >
      <div className="space-y-3">
        <p className="text-[11px] text-muted-foreground">
          Số đã điền theo hợp đồng. Sửa những dòng có thay đổi phát sinh hoặc khấu trừ; dòng chưa
          sửa nghĩa là đã thực hiện đúng như đã ký.
        </p>

        <table className="w-full text-sm">
          <thead>
            <tr className="label-caps">
              <th className="text-left font-normal" />
              <th className="text-right font-normal">Theo HĐ</th>
              <th className="text-right font-normal">Thanh lý</th>
              <th className="text-right font-normal">Chênh lệch</th>
              <th className="text-right font-normal">Đã TT</th>
              <th className="text-right font-normal">Còn lại</th>
            </tr>
          </thead>
          <tbody>
            {BANDS.map(({ key, label }) => {
              const settled = figure(figures[key]);
              const { difference, remaining } = derived(
                settled,
                contracted?.[key] ?? null,
                collected?.[key] ?? null,
              );
              return (
                <tr key={key}>
                  <td className="py-1 pr-2 whitespace-nowrap">{label}</td>
                  <td className="py-1 text-right text-muted-foreground">
                    <Cell value={contracted?.[key] ?? null} />
                  </td>
                  <td className="py-1 pl-2">
                    <input
                      inputMode="numeric"
                      className={INPUT}
                      value={figures[key]}
                      onChange={(event) => {
                        setTouched(true);
                        setFigures((current) => ({ ...current, [key]: event.target.value }));
                      }}
                    />
                  </td>
                  <td className="py-1 pl-2 text-right">
                    <Cell value={difference} />
                  </td>
                  <td className="py-1 pl-2 text-right text-muted-foreground">
                    <Cell value={collected?.[key] ?? null} />
                  </td>
                  <td className="py-1 pl-2 text-right">
                    <Cell value={remaining} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {prefill.data?.refusals?.length ? (
          <div className="text-[11px] text-ember">
            {prefill.data.refusals.map((line) => (
              <p key={line}>{line}</p>
            ))}
          </div>
        ) : null}

        <ErrorState error={prefill.error} />
      </div>
    </Modal>
  );
}

export const ACCEPTANCE_FIGURES_KEY = resultOf("auraos.api.job_acceptance_figures");
