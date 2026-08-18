/**
 * Finance fixture — hardcoded demo data for the finance module.
 * Numbers stay internally consistent with the TVC Tết 2027 fixture:
 * DEAL-0182 / JOB-0182 quote total 850.000.000 ₫, 50% deposit collected.
 */

export type MonthPoint = {
  month: string;
  income: number;
  expense: number;
};

/** Realised months (Jan–Aug 2026) */
export const monthly: MonthPoint[] = [
  { month: "Jan", income: 412_000_000, expense: 318_400_000 },
  { month: "Feb", income: 268_000_000, expense: 231_900_000 },
  { month: "Mar", income: 596_500_000, expense: 441_200_000 },
  { month: "Apr", income: 512_000_000, expense: 396_800_000 },
  { month: "May", income: 734_000_000, expense: 528_300_000 },
  { month: "Jun", income: 648_500_000, expense: 502_100_000 },
  { month: "Jul", income: 881_000_000, expense: 640_700_000 },
  { month: "Aug", income: 525_000_000, expense: 448_600_000 },
];

/** Forecast months (Sep–Dec 2026) with pipeline confidence */
export const forecast = [
  { month: "Sep", committed: 470_000_000, weighted: 182_000_000, expense: 430_000_000, confidence: 0.75 },
  { month: "Oct", committed: 425_000_000, weighted: 316_000_000, expense: 512_000_000, confidence: 0.6 },
  { month: "Nov", committed: 210_000_000, weighted: 498_000_000, expense: 486_000_000, confidence: 0.45 },
  { month: "Dec", committed: 120_000_000, weighted: 742_000_000, expense: 604_000_000, confidence: 0.35 },
];

export type IncomeRow = {
  id: string;
  date: string;
  client: string;
  deal: string;
  invoice: string;
  amount: number;
  vat: number;
  method: "Chuyển khoản" | "Tiền mặt";
  status: "Đã thu" | "Chờ thu" | "Quá hạn";
  due: string;
};

export const incomeRows: IncomeRow[] = [
  {
    id: "IN-2081",
    date: "12 Aug 2026",
    client: "Nhất Minh Beverage",
    deal: "DEAL-0182",
    invoice: "INV-0182-1",
    amount: 425_000_000,
    vat: 42_500_000,
    method: "Chuyển khoản",
    status: "Đã thu",
    due: "12 Aug 2026",
  },
  {
    id: "IN-2082",
    date: "—",
    client: "Nhất Minh Beverage",
    deal: "DEAL-0182",
    invoice: "INV-0182-2",
    amount: 425_000_000,
    vat: 42_500_000,
    method: "Chuyển khoản",
    status: "Chờ thu",
    due: "30 Sep 2026",
  },
  {
    id: "IN-2074",
    date: "28 Jul 2026",
    client: "Bảo Tín Jewelry",
    deal: "DEAL-0171",
    invoice: "INV-0171-2",
    amount: 186_000_000,
    vat: 18_600_000,
    method: "Chuyển khoản",
    status: "Quá hạn",
    due: "27 Jul 2026",
  },
  {
    id: "IN-2069",
    date: "14 Jul 2026",
    client: "Sài Gòn Foods",
    deal: "DEAL-0166",
    invoice: "INV-0166-1",
    amount: 264_000_000,
    vat: 26_400_000,
    method: "Chuyển khoản",
    status: "Đã thu",
    due: "14 Jul 2026",
  },
  {
    id: "IN-2063",
    date: "02 Jul 2026",
    client: "Vietbank Digital",
    deal: "DEAL-0158",
    invoice: "INV-0158-3",
    amount: 148_500_000,
    vat: 14_850_000,
    method: "Chuyển khoản",
    status: "Đã thu",
    due: "02 Jul 2026",
  },
  {
    id: "IN-2058",
    date: "—",
    client: "Hải Đăng Retail",
    deal: "DEAL-0149",
    invoice: "INV-0149-2",
    amount: 92_000_000,
    vat: 9_200_000,
    method: "Tiền mặt",
    status: "Quá hạn",
    due: "18 Jun 2026",
  },
];

export type ExpenseRow = {
  id: string;
  date: string;
  what: string;
  category: string;
  job: string;
  payee: string;
  taxType: "Công ty" | "Cá nhân" | "Không hoá đơn";
  amount: number;
  status: "Đã trả" | "Chờ trả" | "Chờ đối chiếu";
};

export const expenseRows: ExpenseRow[] = [
  {
    id: "EX-4412",
    date: "18 Aug 2026",
    what: "Catering day 2 — 41 pax",
    category: "Catering",
    job: "JOB-0182",
    payee: "Bếp Cô Ba",
    taxType: "Không hoá đơn",
    amount: 9_800_000,
    status: "Chờ đối chiếu",
  },
  {
    id: "EX-4408",
    date: "17 Aug 2026",
    what: "Arri Alexa 35 + kit — 3 ngày",
    category: "Equipment",
    job: "JOB-0182",
    payee: "Lens Rental SG",
    taxType: "Công ty",
    amount: 96_000_000,
    status: "Đã trả",
  },
  {
    id: "EX-4402",
    date: "16 Aug 2026",
    what: "DOP — Nguyễn Trung Hiếu",
    category: "Crew",
    job: "JOB-0182",
    payee: "Nguyễn Trung Hiếu",
    taxType: "Cá nhân",
    amount: 60_000_000,
    status: "Chờ trả",
  },
  {
    id: "EX-4396",
    date: "14 Aug 2026",
    what: "Art dept — props hoa mai",
    category: "Art",
    job: "JOB-0182",
    payee: "Xưởng Art Minh Trí",
    taxType: "Công ty",
    amount: 38_400_000,
    status: "Đã trả",
  },
  {
    id: "EX-4381",
    date: "09 Aug 2026",
    what: "Studio rental — Long Vân",
    category: "Production",
    job: "JOB-0171",
    payee: "Long Vân Studio",
    taxType: "Công ty",
    amount: 45_000_000,
    status: "Đã trả",
  },
  {
    id: "EX-4370",
    date: "05 Aug 2026",
    what: "Grading + online",
    category: "Post-production",
    job: "JOB-0171",
    payee: "Colorist Hồ Anh Duy",
    taxType: "Cá nhân",
    amount: 32_000_000,
    status: "Chờ trả",
  },
  {
    id: "EX-4362",
    date: "02 Aug 2026",
    what: "Văn phòng — tiền thuê tháng 8",
    category: "Overhead",
    job: "—",
    payee: "Toà nhà Phú Mỹ",
    taxType: "Công ty",
    amount: 42_000_000,
    status: "Đã trả",
  },
];

export const expenseByCategory = [
  { category: "Crew", amount: 1_284_000_000 },
  { category: "Equipment", amount: 862_000_000 },
  { category: "Art", amount: 486_000_000 },
  { category: "Post-production", amount: 398_000_000 },
  { category: "Catering & transport", amount: 214_000_000 },
  { category: "Overhead", amount: 336_000_000 },
];

export const cashAccounts = [
  { name: "Vietcombank — công ty", balance: 918_400_000, kind: "Ngân hàng" },
  { name: "Techcombank — thuế & VAT", balance: 246_000_000, kind: "Ngân hàng" },
  { name: "Quỹ tiền mặt studio", balance: 38_500_000, kind: "Tiền mặt" },
  { name: "Float đang giữ bởi crew", balance: 27_100_000, kind: "Tạm ứng" },
];

/** Aged receivables / payables */
export const receivables = [
  { bucket: "Chưa đến hạn", amount: 425_000_000 },
  { bucket: "1–30 ngày", amount: 186_000_000 },
  { bucket: "31–60 ngày", amount: 92_000_000 },
  { bucket: "60+ ngày", amount: 0 },
];

export const payables = [
  { bucket: "Chưa đến hạn", amount: 92_000_000 },
  { bucket: "1–30 ngày", amount: 60_000_000 },
  { bucket: "31–60 ngày", amount: 32_000_000 },
  { bucket: "60+ ngày", amount: 0 },
];

export const jobProfitability = [
  { job: "JOB-0182", name: 'TVC Tết 2027 "Vị Xuân"', revenue: 850_000_000, cost: 612_000_000 },
  { job: "JOB-0171", name: "Bảo Tín — Brand film", revenue: 372_000_000, cost: 268_400_000 },
  { job: "JOB-0166", name: "Sài Gòn Foods — KV shoot", revenue: 264_000_000, cost: 214_800_000 },
  { job: "JOB-0158", name: "Vietbank — Digital series", revenue: 445_500_000, cost: 296_100_000 },
  { job: "JOB-0149", name: "Hải Đăng — Retail TVC", revenue: 184_000_000, cost: 161_200_000 },
];

export const taxLines = [
  { label: "VAT đầu ra (Q3)", amount: 111_400_000 },
  { label: "VAT đầu vào được trừ", amount: -62_800_000 },
  { label: "TNCN khấu trừ freelancer", amount: 24_600_000 },
  { label: "TNDN tạm tính 20%", amount: 96_200_000 },
];

export const sum = (ns: number[]) => ns.reduce((a, b) => a + b, 0);

export const ytd = {
  income: sum(monthly.map((m) => m.income)),
  expense: sum(monthly.map((m) => m.expense)),
};

export const ytdProfit = ytd.income - ytd.expense;
export const ytdMarginPct = Math.round((ytdProfit / ytd.income) * 1000) / 10;
