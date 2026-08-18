import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import {
  Search,
  Plus,
  FileText,
  Bold,
  Italic,
  Underline,
  List,
  Link2,
  Undo2,
  Redo2,
  Download,
  RotateCcw,
} from "lucide-react";
import { AppShell } from "@/components/aura/AppShell";
import { Card, Pill } from "@/components/aura/primitives";
import { deal } from "@/data/fixture";

export const Route = createFileRoute("/paperwork")({
  head: () => ({
    meta: [
      { title: "Paperwork — document workspace | AuraOS" },
      {
        name: "description",
        content:
          "Generate contracts and appendices from templates, edit them inline, fill gap markers and export to .docx.",
      },
      { property: "og:title", content: "Paperwork — document workspace" },
      {
        property: "og:description",
        content: "Document list, inline editor and gap markers in one internal workspace.",
      },
    ],
  }),
  component: PaperworkPage,
});

const docs = [
  {
    group: "Hợp đồng dịch vụ",
    items: [
      { name: "HĐ Nhất Minh Beverage — Vị Xuân", party: "Nhất Minh Beverage", status: "Draft", when: "2h ago" },
      { name: "HĐ Hải Đăng Rental — camera", party: "Hải Đăng Rental", status: "Signed", when: "3 days ago" },
    ],
  },
  {
    group: "Phụ lục",
    items: [
      { name: "Phụ lục 01 — change order R3", party: "Nhất Minh Beverage", status: "Awaiting signature", when: "Yesterday" },
    ],
  },
  {
    group: "Biên bản",
    items: [
      { name: "BB bàn giao — TVC 30s", party: "Nhất Minh Beverage", status: "Draft", when: "6 days ago" },
      { name: "BB thanh toán — Vũ Đình Nam", party: "Vũ Đình Nam", status: "Signed", when: "1 week ago" },
    ],
  },
];

const statusTone: Record<string, string> = {
  Draft: "neutral",
  "Awaiting signature": "ember",
  Signed: "ink",
};

const gaps = [
  { token: "{{ngay_ky}}", label: "Ngày ký hợp đồng" },
  { token: "{{so_tai_khoan}}", label: "Số tài khoản bên A" },
  { token: "{{nguoi_dai_dien}}", label: "Người đại diện bên A" },
];

const versions = [
  { label: "Current draft", when: "Today 14:02", who: "Trần Quốc Bảo" },
  { label: "Save 3", when: "Today 11:20", who: "Trần Mỹ Linh" },
  { label: "Save 2", when: "Yesterday 17:45", who: "Trần Quốc Bảo" },
  { label: "Generated from template", when: "17 Aug 09:30", who: "System" },
];

const filters = ["All", "Drafts", "Awaiting signature", "Signed"];

function PaperworkPage() {
  const [mode, setMode] = useState<"edit" | "preview">("edit");
  const [filter, setFilter] = useState("All");
  const [selected, setSelected] = useState("HĐ Nhất Minh Beverage — Vị Xuân");

  return (
    <AppShell
      title="Paperwork"
      meta="5 documents · 3 gaps remaining on the open draft"
      actions={
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-medium hover:bg-secondary">
            <Download className="size-3.5" /> Export .docx
          </button>
          <button className="inline-flex items-center gap-1.5 rounded-lg bg-ember px-3 py-2 text-xs font-medium text-ember-foreground hover:opacity-90">
            <Plus className="size-3.5" /> New from template
          </button>
        </div>
      }
    >
      <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)_290px]">
        {/* document list */}
        <Card className="h-fit" title="Documents">
          <div className="border-b border-border p-3">
            <div className="flex items-center gap-2 rounded-lg border border-border px-2.5 py-1.5">
              <Search className="size-3.5 text-muted-foreground" />
              <input
                placeholder="Search documents"
                className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              />
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {filters.map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={
                    filter === f
                      ? "rounded-md bg-primary px-2 py-1 text-[11px] font-medium text-primary-foreground"
                      : "rounded-md px-2 py-1 text-[11px] text-muted-foreground hover:bg-secondary"
                  }
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
          <div className="max-h-[540px] overflow-y-auto">
            {docs.map((g) => (
              <div key={g.group}>
                <div className="label-caps bg-secondary/60 px-3 py-1.5">{g.group}</div>
                <ul className="divide-y divide-border">
                  {g.items
                    .filter(
                      (d) =>
                        filter === "All" ||
                        (filter === "Drafts" ? d.status === "Draft" : d.status === filter),
                    )
                    .map((d) => (
                      <li key={d.name}>
                        <button
                          onClick={() => setSelected(d.name)}
                          className={`flex w-full gap-2 px-3 py-2.5 text-left hover:bg-secondary/60 ${
                            selected === d.name ? "bg-secondary" : ""
                          }`}
                        >
                          <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                          <div className="min-w-0">
                            <div className="truncate text-sm font-medium">{d.name}</div>
                            <div className="mt-0.5 truncate text-xs text-muted-foreground">
                              {d.party} · {d.when}
                            </div>
                            <Pill tone={statusTone[d.status]} className="mt-1.5">
                              {d.status}
                            </Pill>
                          </div>
                        </button>
                      </li>
                    ))}
                </ul>
              </div>
            ))}
          </div>
        </Card>

        {/* editor canvas */}
        <Card
          title={selected}
          subtitle={`${deal.client} · ${deal.code} · saved 2 minutes ago`}
          action={
            <div className="flex rounded-lg border border-border p-0.5">
              {(["edit", "preview"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={
                    mode === m
                      ? "rounded-md bg-primary px-2.5 py-1 text-[11px] font-medium text-primary-foreground capitalize"
                      : "rounded-md px-2.5 py-1 text-[11px] text-muted-foreground capitalize hover:bg-secondary"
                  }
                >
                  {m}
                </button>
              ))}
            </div>
          }
        >
          {mode === "edit" ? (
            <div className="flex flex-wrap items-center gap-1 border-b border-border px-3 py-2">
              {[Undo2, Redo2].map((I, i) => (
                <button key={i} className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary">
                  <I className="size-4" />
                </button>
              ))}
              <span className="mx-1 h-5 w-px bg-border" />
              <select className="rounded-md border border-border bg-transparent px-2 py-1 text-xs">
                <option>Body text</option>
                <option>Heading 1</option>
                <option>Heading 2</option>
              </select>
              <span className="mx-1 h-5 w-px bg-border" />
              {[Bold, Italic, Underline, List, Link2].map((I, i) => (
                <button key={i} className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary">
                  <I className="size-4" />
                </button>
              ))}
            </div>
          ) : null}

          <div className="max-h-[620px] overflow-y-auto bg-secondary/40 p-4 sm:p-6">
            <article className="doc-page mx-auto max-w-[720px] rounded-md border border-border bg-card px-8 py-10 text-[13px] leading-relaxed shadow-sm">
              <p className="text-center text-xs tracking-wide text-muted-foreground uppercase">
                Công ty TNHH Aura Production
              </p>
              <h1 className="mt-6 text-center font-display text-lg font-semibold">
                HỢP ĐỒNG DỊCH VỤ SẢN XUẤT PHIM QUẢNG CÁO
              </h1>
              <p className="mt-1 text-center text-xs text-muted-foreground">
                Số: HĐ-2026/AURA-NMB-018
              </p>

              <p className="mt-6">
                Hôm nay, ngày <Gap mode={mode}>{"{{ngay_ky}}"}</Gap>, tại Thành phố Hồ Chí Minh,
                chúng tôi gồm:
              </p>

              <h2 className="mt-5 font-semibold">Bên A — Bên sử dụng dịch vụ</h2>
              <p className="mt-1">
                Công ty: <strong>Nhất Minh Beverage</strong>
                <br />
                Người đại diện: <Gap mode={mode}>{"{{nguoi_dai_dien}}"}</Gap>
                <br />
                Số tài khoản: <Gap mode={mode}>{"{{so_tai_khoan}}"}</Gap>
              </p>

              <h2 className="mt-5 font-semibold">Bên B — Bên cung cấp dịch vụ</h2>
              <p className="mt-1">
                Công ty TNHH Aura Production, đại diện bởi ông Trần Quốc Bảo, Giám đốc.
              </p>

              <h2 className="mt-5 font-semibold">Điều 1. Nội dung công việc</h2>
              <p className="mt-1">
                Bên B thực hiện sản xuất phim quảng cáo {deal.name} bao gồm ba gói công việc: tiền
                kỳ và ý tưởng, sản xuất hai ngày ghi hình, hậu kỳ và bàn giao.
              </p>

              <h2 className="mt-5 font-semibold">Điều 2. Giá trị hợp đồng</h2>
              <p className="mt-1">
                Tổng giá trị hợp đồng: <strong className="num">736.560.000 ₫</strong> (đã bao gồm
                thuế GTGT 8%). Thanh toán theo ba mốc: 40% đặt cọc, 30% sau ghi hình, 30% khi bàn
                giao.
              </p>
            </article>
          </div>
        </Card>

        {/* right rail */}
        <div className="space-y-4">
          <Card title={`${gaps.length} gaps remaining`} subtitle="Unfilled tokens in this document">
            <ul className="divide-y divide-border">
              {gaps.map((g) => (
                <li key={g.token} className="flex items-center gap-2 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium">{g.label}</div>
                    <div className="num mt-0.5 truncate text-[11px] text-ember">{g.token}</div>
                  </div>
                  <button className="rounded-md border border-border px-2 py-1 text-xs hover:bg-secondary">
                    Fill
                  </button>
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Version history">
            <ul className="divide-y divide-border">
              {versions.map((v, i) => (
                <li key={v.label} className="flex items-center gap-2 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium">{v.label}</div>
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {v.when} · {v.who}
                    </div>
                  </div>
                  {i > 0 ? (
                    <button className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs hover:bg-secondary">
                      <RotateCcw className="size-3" /> Restore
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

function Gap({ children, mode }: { children: string; mode: "edit" | "preview" }) {
  if (mode === "preview") {
    return <span className="rounded bg-ember-soft px-1 text-ember">[ chưa điền ]</span>;
  }
  return (
    <span className="num rounded border border-dashed border-ember bg-ember-soft px-1 text-[12px] text-ember">
      {children}
    </span>
  );
}
