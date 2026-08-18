/**
 * Shared fixture: TVC Tết 2027 "Vị Xuân"
 * Mirrors docs/ui-exploration/fixture-tvc-tet-2027.md exactly.
 * Figures are internally consistent — do not round or re-derive them.
 */

export const deal = {
  name: 'TVC Tết 2027 "Vị Xuân"',
  code: "DEAL-0182",
  client: "Nhất Minh Beverage",
  contact: "Chị Phạm Thu Hà, Marketing Director",
  owner: "Trần Quốc Bảo",
  tier: "Tier 3",
  positioning: "Brand",
  stage: "Breakdown",
  clientBudget: 850_000_000,
};

export type TaxType = "Công ty" | "Cá nhân" | "Không hoá đơn";

export type CostLine = {
  id: number;
  description: string;
  category: string;
  phase: "Pre-production" | "Production" | "Post-production";
  source: "Internal" | "Freelancer" | "Vendor";
  contact: string;
  pkg: "P1" | "P2" | "P3";
  qty1: number;
  unit1: string;
  qty2?: number;
  unit2?: string;
  unitPrice: number;
  taxType: TaxType;
  markup: number;
  subtotal: number;
  quotePrice: number;
};

export const costLines: CostLine[] = [
  {
    id: 1,
    description: "Creative concept & script",
    category: "Creative",
    phase: "Pre-production",
    source: "Internal",
    contact: "Studio",
    pkg: "P1",
    qty1: 1,
    unit1: "job",
    unitPrice: 25_000_000,
    taxType: "Công ty",
    markup: 20,
    subtotal: 25_000_000,
    quotePrice: 30_000_000,
  },
  {
    id: 2,
    description: "Storyboard artist",
    category: "Creative",
    phase: "Pre-production",
    source: "Freelancer",
    contact: "Lê Minh Khoa",
    pkg: "P1",
    qty1: 12,
    unit1: "frames",
    unitPrice: 800_000,
    taxType: "Cá nhân",
    markup: 15,
    subtotal: 9_600_000,
    quotePrice: 11_040_000,
  },
  {
    id: 3,
    description: "Location scouting & permits",
    category: "Production",
    phase: "Pre-production",
    source: "Vendor",
    contact: "An Lộc Location",
    pkg: "P1",
    qty1: 3,
    unit1: "days",
    unitPrice: 4_000_000,
    taxType: "Không hoá đơn",
    markup: 10,
    subtotal: 12_000_000,
    quotePrice: 13_200_000,
  },
  {
    id: 4,
    description: "Casting - talent search",
    category: "Talent",
    phase: "Pre-production",
    source: "Vendor",
    contact: "Casting Sài Gòn",
    pkg: "P1",
    qty1: 1,
    unit1: "job",
    unitPrice: 15_000_000,
    taxType: "Công ty",
    markup: 15,
    subtotal: 15_000_000,
    quotePrice: 17_250_000,
  },
  {
    id: 5,
    description: "Director",
    category: "Crew",
    phase: "Production",
    source: "Freelancer",
    contact: "Nguyễn Hoàng Duy",
    pkg: "P2",
    qty1: 2,
    unit1: "days",
    unitPrice: 18_000_000,
    taxType: "Cá nhân",
    markup: 15,
    subtotal: 36_000_000,
    quotePrice: 41_400_000,
  },
  {
    id: 6,
    description: "DOP + camera team",
    category: "Crew",
    phase: "Production",
    source: "Freelancer",
    contact: "Vũ Đình Nam",
    pkg: "P2",
    qty1: 2,
    unit1: "days",
    qty2: 4,
    unit2: "crew",
    unitPrice: 22_000_000,
    taxType: "Cá nhân",
    markup: 15,
    subtotal: 44_000_000,
    quotePrice: 50_600_000,
  },
  {
    id: 7,
    description: "Camera package - Alexa Mini LF",
    category: "Equipment",
    phase: "Production",
    source: "Vendor",
    contact: "Hải Đăng Rental",
    pkg: "P2",
    qty1: 2,
    unit1: "days",
    unitPrice: 28_000_000,
    taxType: "Công ty",
    markup: 20,
    subtotal: 56_000_000,
    quotePrice: 67_200_000,
  },
  {
    id: 8,
    description: "Lighting & grip package",
    category: "Equipment",
    phase: "Production",
    source: "Vendor",
    contact: "Hải Đăng Rental",
    pkg: "P2",
    qty1: 2,
    unit1: "days",
    unitPrice: 19_000_000,
    taxType: "Công ty",
    markup: 20,
    subtotal: 38_000_000,
    quotePrice: 45_600_000,
  },
  {
    id: 9,
    description: "Art department & set build",
    category: "Art",
    phase: "Production",
    source: "Vendor",
    contact: "Xưởng Mộc Tân Phú",
    pkg: "P2",
    qty1: 1,
    unit1: "job",
    unitPrice: 85_000_000,
    taxType: "Công ty",
    markup: 18,
    subtotal: 85_000_000,
    quotePrice: 100_300_000,
  },
  {
    id: 10,
    description: "Lead talent - 3 cast",
    category: "Talent",
    phase: "Production",
    source: "Freelancer",
    contact: "Various",
    pkg: "P2",
    qty1: 3,
    unit1: "cast",
    unitPrice: 12_000_000,
    taxType: "Cá nhân",
    markup: 15,
    subtotal: 36_000_000,
    quotePrice: 41_400_000,
  },
  {
    id: 11,
    description: "Studio rental",
    category: "Location",
    phase: "Production",
    source: "Vendor",
    contact: "Phim Trường Đông Sài Gòn",
    pkg: "P2",
    qty1: 2,
    unit1: "days",
    unitPrice: 15_000_000,
    taxType: "Công ty",
    markup: 15,
    subtotal: 30_000_000,
    quotePrice: 34_500_000,
  },
  {
    id: 12,
    description: "Catering & transport",
    category: "Production",
    phase: "Production",
    source: "Vendor",
    contact: "Bếp Nhà Mai",
    pkg: "P2",
    qty1: 2,
    unit1: "days",
    qty2: 35,
    unit2: "pax",
    unitPrice: 8_500_000,
    taxType: "Không hoá đơn",
    markup: 10,
    subtotal: 17_000_000,
    quotePrice: 18_700_000,
  },
  {
    id: 13,
    description: "Offline edit",
    category: "Post",
    phase: "Post-production",
    source: "Freelancer",
    contact: "Đặng Thu Trang",
    pkg: "P3",
    qty1: 8,
    unit1: "days",
    unitPrice: 3_500_000,
    taxType: "Cá nhân",
    markup: 15,
    subtotal: 28_000_000,
    quotePrice: 32_200_000,
  },
  {
    id: 14,
    description: "Colour grading",
    category: "Post",
    phase: "Post-production",
    source: "Vendor",
    contact: "Sắc Màu Post",
    pkg: "P3",
    qty1: 2,
    unit1: "days",
    unitPrice: 12_000_000,
    taxType: "Công ty",
    markup: 20,
    subtotal: 24_000_000,
    quotePrice: 28_800_000,
  },
  {
    id: 15,
    description: "Sound design & mix",
    category: "Post",
    phase: "Post-production",
    source: "Vendor",
    contact: "Âm Thanh Việt",
    pkg: "P3",
    qty1: 1,
    unit1: "job",
    unitPrice: 18_000_000,
    taxType: "Công ty",
    markup: 20,
    subtotal: 18_000_000,
    quotePrice: 21_600_000,
  },
  {
    id: 16,
    description: "Music licence",
    category: "Post",
    phase: "Post-production",
    source: "Vendor",
    contact: "Universal Production Music",
    pkg: "P3",
    qty1: 1,
    unit1: "track",
    unitPrice: 35_000_000,
    taxType: "Công ty",
    markup: 10,
    subtotal: 35_000_000,
    quotePrice: 38_500_000,
  },
  {
    id: 17,
    description: "VFX & motion graphics",
    category: "Post",
    phase: "Post-production",
    source: "Freelancer",
    contact: "Studio Bốn Mùa",
    pkg: "P3",
    qty1: 1,
    unit1: "job",
    unitPrice: 22_000_000,
    taxType: "Cá nhân",
    markup: 15,
    subtotal: 22_000_000,
    quotePrice: 25_300_000,
  },
];

export const costTotals = {
  totalCost: 530_600_000,
  totalLineQuote: 617_590_000,
};

export const packages = [
  {
    pkg: "P1",
    title: "Pre-production & concept",
    description: "Script, storyboard, casting, recce and permits",
    memberSum: 71_490_000,
    override: 72_000_000,
    price: 72_000_000,
    variance: 510_000,
  },
  {
    pkg: "P2",
    title: "Production - 2 shoot days",
    description: "Crew, cast, camera, lighting, art and studio",
    memberSum: 399_700_000,
    override: 400_000_000,
    price: 400_000_000,
    variance: 300_000,
  },
  {
    pkg: "P3",
    title: "Post-production & delivery",
    description: "Edit, grade, sound, music licence, VFX, masters",
    memberSum: 146_400_000,
    override: 148_000_000,
    price: 148_000_000,
    variance: 1_600_000,
  },
];

export const totals = {
  packagesSubtotal: 620_000_000,
  managementFeeRate: 10,
  managementFee: 62_000_000,
  beforeVat: 682_000_000,
  vatRate: 8,
  vat: 54_560_000,
  total: 736_560_000,
  cost: 530_600_000,
  margin: 151_400_000,
  marginPct: 22.2,
  marginFloorPct: 20,
};

export const founderBlock = {
  commissionRate: 5,
  commission: 34_100_000,
  cmAfterCommission: 117_300_000,
  profitBeforeTax: 117_300_000,
  tndnRate: 20,
  tndn: 23_460_000,
  netProfit: 93_840_000,
  vatPayable: 54_560_000,
};

export const quoteVersions = [
  {
    version: "v1",
    status: "Sent",
    total: 712_800_000,
    published: "05 Aug 2026",
    opens: "4 opens, last 09 Aug",
  },
  {
    version: "v2",
    status: "Published",
    total: 736_560_000,
    published: "17 Aug 2026",
    opens: "not opened yet",
  },
];

export const quoteDetailLevel = "Package totals - one price per package";

export const dashboardTiles = [
  { label: "Pipeline (open deals)", value: 1_925_000_000, sub: "6 open deals" },
  { label: "In production", value: 815_000_000, sub: "4 open jobs" },
  { label: "Overdue payments", value: 86_500_000, sub: "2 milestones past terms", alert: true },
  { label: "Quotes gone quiet", value: 95_000_000, sub: "past 7 days", alert: true },
];

export const jobsInProduction = [
  {
    job: "Factory safety series",
    client: "Sông Hà Logistics",
    quoted: 210_000_000,
    stage: "Production",
  },
  {
    job: 'Brand film "Hạt Gạo Quê"',
    client: "Lộc Trời Agri",
    quoted: 380_000_000,
    stage: "Post-production",
  },
  {
    job: "Tết campaign cutdowns",
    client: "Gốm Sứ Minh Long",
    quoted: 95_000_000,
    stage: "Delivery",
  },
  {
    job: "Recruitment film",
    client: "Đại Việt Foods",
    quoted: 130_000_000,
    stage: "Awaiting payment",
  },
];

export const needsAttention = [
  {
    kind: "Overdue milestone",
    what: "Tết campaign cutdowns - 50% on delivery",
    amount: 47_500_000,
    age: "12 days overdue",
  },
  {
    kind: "Overdue milestone",
    what: "Recruitment film - final 30%",
    amount: 39_000_000,
    age: "5 days overdue",
  },
  {
    kind: "Silent quote",
    what: "Social cutdowns x12 - Nhất Minh Beverage",
    amount: 95_000_000,
    age: "9 days no reply",
  },
];

export const expenseCategories = [
  "Crew",
  "Equipment",
  "Art",
  "Catering",
  "Transport",
  "Uncategorised",
];

// Money formatting is not fixture data. It lives in lib/format.ts, which is the
// one formatter every screen uses; this re-export exists only so the screens
// still on fixtures keep working until their own tickets convert them.
export { vnd } from "@/lib/format";
