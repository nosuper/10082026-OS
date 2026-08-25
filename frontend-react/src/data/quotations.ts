import { costLines, packages } from "@/data/fixture";

export type QuoteLine = {
  id: string;
  /** "divider" rows are section titles / free text — no price, no maths */
  kind?: "package" | "divider" | undefined;
  label: string;
  note?: string | undefined;
  /** Template package this line started from, if any */
  templatePkg?: string | undefined;
  /** Breakdown lines that make up this package line — editable */
  lineIds: number[];
  qty: number;
  unit: string;
  qty2?: number | undefined;
  unit2?: string | undefined;
  /** null = use the summed price from the breakdown members */
  overrideUnitPrice: number | null;
};

export const unitOptions = [
  "package",
  "job",
  "day",
  "days",
  "shoot day",
  "frames",
  "cast",
  "crew",
  "pax",
  "track",
  "item",
  "set",
];

export const clientContacts = [
  { name: "Chị Phạm Thu Hà", role: "Marketing Director", email: "ha.pham@nhatminh.vn" },
  { name: "Anh Đỗ Quang Vinh", role: "Brand Manager", email: "vinh.do@nhatminh.vn" },
  { name: "Chị Lý Kim Ngân", role: "Procurement", email: "ngan.ly@nhatminh.vn" },
  { name: "Anh Bùi Trọng Nghĩa", role: "CFO", email: "nghia.bui@nhatminh.vn" },
];

export function memberSum(lineIds: number[]): number {
  return costLines.filter((l) => lineIds.includes(l.id)).reduce((a, l) => a + l.quotePrice, 0);
}

export function isDivider(l: QuoteLine): boolean {
  return l.kind === "divider";
}

export function lineUnitPrice(l: QuoteLine): number {
  if (isDivider(l)) return 0;
  return l.overrideUnitPrice ?? memberSum(l.lineIds);
}

export function lineAmount(l: QuoteLine): number {
  if (isDivider(l)) return 0;
  return Math.round(lineUnitPrice(l) * (l.qty || 0) * (l.qty2 && l.qty2 > 0 ? l.qty2 : 1));
}

export function packageLineIds(pkg: string): number[] {
  return costLines.filter((l) => l.pkg === pkg).map((l) => l.id);
}

export const packageTemplates = packages.map((p) => ({
  pkg: p.pkg,
  title: p.title,
  description: p.description,
  lineIds: packageLineIds(p.pkg),
  sum: p.memberSum,
}));

export const seedQuoteLines: QuoteLine[] = [
  {
    id: "L1",
    label: "Pre-production & concept",
    note: "Script, storyboard, casting, recce and permits",
    templatePkg: "P1",
    lineIds: packageLineIds("P1"),
    qty: 1,
    unit: "package",
    overrideUnitPrice: 72_000_000,
  },
  {
    id: "D1",
    kind: "divider",
    label: "Production block — 2 shoot days at Bình Dương studio",
    lineIds: [],
    qty: 0,
    unit: "package",
    overrideUnitPrice: 0,
  },
  {
    id: "L2",
    label: "Production — shoot days",
    note: "Crew, cast, camera, lighting, art and studio",
    templatePkg: "P2",
    lineIds: packageLineIds("P2"),
    qty: 2,
    unit: "shoot day",
    qty2: 1,
    unit2: "unit",
    overrideUnitPrice: 200_000_000,
  },
  {
    id: "L3",
    label: "Post-production & delivery",
    note: "Edit, grade, sound, music licence, VFX, masters",
    templatePkg: "P3",
    lineIds: packageLineIds("P3"),
    qty: 1,
    unit: "package",
    overrideUnitPrice: 148_000_000,
  },
];

export type OpenEvent = {
  when: string;
  who: string;
  where: string;
  device: string;
  detail: string;
};

export const seedOpenLog: OpenEvent[] = [
  {
    when: "17 Aug 2026 · 09:12",
    who: "Chị Phạm Thu Hà",
    where: "Ho Chi Minh City, VN",
    device: "iPhone · Safari",
    detail: "Opened link · viewed 2m 41s",
  },
  {
    when: "17 Aug 2026 · 09:20",
    who: "Chị Phạm Thu Hà",
    where: "Ho Chi Minh City, VN",
    device: "iPhone · Safari",
    detail: "Downloaded PDF",
  },
  {
    when: "16 Aug 2026 · 15:48",
    who: "Unknown (forwarded)",
    where: "Hanoi, VN",
    device: "Windows · Chrome",
    detail: "Opened link · viewed 48s",
  },
  {
    when: "15 Aug 2026 · 11:02",
    who: "Trần Quốc Bảo",
    where: "Ho Chi Minh City, VN",
    device: "macOS · Chrome",
    detail: "Published v2 · link created",
  },
];

export type VersionSnapshot = {
  version: string;
  name: string;
  status: "Draft" | "Sent" | "Published" | "Accepted";
  published: string;
  subtotal: number;
  feeRate: number;
  vatRate: number;
  total: number;
  cost: number;
  lines: { label: string; amount: number }[];
};

export const versionSnapshots: VersionSnapshot[] = [
  {
    version: "v2",
    name: 'Quotation — TVC Tết 2027 "Vị Xuân"',
    status: "Published",
    published: "17 Aug 2026",
    subtotal: 620_000_000,
    feeRate: 10,
    vatRate: 8,
    total: 736_560_000,
    cost: 530_600_000,
    lines: [
      { label: "Pre-production & concept", amount: 72_000_000 },
      { label: "Production — shoot days", amount: 400_000_000 },
      { label: "Post-production & delivery", amount: 148_000_000 },
    ],
  },
  {
    version: "v1",
    name: "Quotation — TVC Tết 2027 (option 1 shoot day)",
    status: "Sent",
    published: "05 Aug 2026",
    subtotal: 600_000_000,
    feeRate: 10,
    vatRate: 8,
    total: 712_800_000,
    cost: 486_000_000,
    lines: [
      { label: "Pre-production & concept", amount: 68_000_000 },
      { label: "Production — shoot days", amount: 392_000_000 },
      { label: "Post-production & delivery", amount: 140_000_000 },
    ],
  },
  {
    version: "v2-B",
    name: "Option B — lean crew, single location",
    status: "Draft",
    published: "16 Aug 2026",
    subtotal: 548_000_000,
    feeRate: 8,
    vatRate: 8,
    total: 639_244_800,
    cost: 452_800_000,
    lines: [
      { label: "Pre-production & concept", amount: 62_000_000 },
      { label: "Production — shoot days", amount: 356_000_000 },
      { label: "Post-production & delivery", amount: 118_000_000 },
      { label: "Social cutdowns x6", amount: 12_000_000 },
    ],
  },
  {
    version: "v2-C",
    name: "Option C — premium, 3 shoot days + celebrity",
    status: "Draft",
    published: "17 Aug 2026",
    subtotal: 812_000_000,
    feeRate: 12,
    vatRate: 8,
    total: 982_195_200,
    cost: 660_400_000,
    lines: [
      { label: "Pre-production & concept", amount: 88_000_000 },
      { label: "Production — shoot days", amount: 548_000_000 },
      { label: "Post-production & delivery", amount: 176_000_000 },
    ],
  },
];

export type VersionShare = {
  version: string;
  name: string;
  status: VersionSnapshot["status"];
  slug: string;
  recipient: string;
  published: string;
  lastOpen: string | null;
  log: OpenEvent[];
};

export const versionShares: VersionShare[] = [
  {
    version: "v2",
    name: 'Quotation — TVC Tết 2027 "Vị Xuân"',
    status: "Published",
    slug: "quo-0182-2-x7f2",
    recipient: "ha.pham@nhatminh.vn",
    published: "17 Aug 2026",
    lastOpen: "17 Aug 2026 · 09:20",
    log: seedOpenLog,
  },
  {
    version: "v2-C",
    name: "Option C — premium, 3 shoot days + celebrity",
    status: "Draft",
    slug: "quo-0182-2c-m4k9",
    recipient: "vinh.do@nhatminh.vn",
    published: "17 Aug 2026",
    lastOpen: "17 Aug 2026 · 18:04",
    log: [
      {
        when: "17 Aug 2026 · 18:04",
        who: "Anh Đỗ Quang Vinh",
        where: "Ho Chi Minh City, VN",
        device: "macOS · Chrome",
        detail: "Opened link · viewed 3m 12s",
      },
      {
        when: "17 Aug 2026 · 17:50",
        who: "Trần Quốc Bảo",
        where: "Ho Chi Minh City, VN",
        device: "macOS · Chrome",
        detail: "Published v2-C · link created",
      },
    ],
  },
  {
    version: "v2-B",
    name: "Option B — lean crew, single location",
    status: "Draft",
    slug: "quo-0182-2b-p1zq",
    recipient: "ngan.ly@nhatminh.vn",
    published: "16 Aug 2026",
    lastOpen: null,
    log: [
      {
        when: "16 Aug 2026 · 11:30",
        who: "Trần Quốc Bảo",
        where: "Ho Chi Minh City, VN",
        device: "macOS · Chrome",
        detail: "Draft link created · not sent",
      },
    ],
  },
  {
    version: "v1",
    name: "Quotation — TVC Tết 2027 (option 1 shoot day)",
    status: "Sent",
    slug: "quo-0182-1-b8we",
    recipient: "ha.pham@nhatminh.vn",
    published: "05 Aug 2026",
    lastOpen: "07 Aug 2026 · 14:11",
    log: [
      {
        when: "07 Aug 2026 · 14:11",
        who: "Chị Phạm Thu Hà",
        where: "Ho Chi Minh City, VN",
        device: "iPhone · Safari",
        detail: "Opened link · viewed 1m 07s",
      },
      {
        when: "06 Aug 2026 · 08:42",
        who: "Anh Bùi Trọng Nghĩa",
        where: "Hanoi, VN",
        device: "Windows · Edge",
        detail: "Downloaded PDF",
      },
      {
        when: "05 Aug 2026 · 16:20",
        who: "Trần Quốc Bảo",
        where: "Ho Chi Minh City, VN",
        device: "macOS · Chrome",
        detail: "Published v1 · link created",
      },
    ],
  },
];
