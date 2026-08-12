# TÀI LIỆU KỸ THUẬT: SETUP HỆ THỐNG QUẢN LÝ PRODUCTION HOUSE
## Dành cho Engineer — triển khai bám sát Playbook vận hành của Founder

> Mục tiêu: dựng hệ thống mô hình hóa đúng quy trình trong Playbook (tài liệu 01): một pipeline duy nhất 10 trạm, phân tier, quotation 2 lớp (internal cost ↔ client quote), phân luồng vendor cá nhân/công ty, tracking budget vs actual và margin theo loại job. Team <10 người, ưu tiên open-source/self-hosted, có lộ trình scale.

---

## PHẦN 1 — KIẾN TRÚC TỔNG THỂ (Stack A)

```
┌─────────────────────────────────────────────────────────┐
│  TRỤC XƯƠNG SỐNG: Odoo 17/18 Community (self-hosted)    │
│  CRM (pipeline+tier) → Sales (quotation) → Project      │
│  → Invoicing (nội bộ) → Analytic Accounts (margin/job)  │
└──────────────┬──────────────────────────────────────────┘
               │ (link/manual bridge)
   ┌───────────┼────────────────┬─────────────────────┐
   ▼           ▼                ▼                     ▼
StudioBinder  Frame.io      MISA meInvoice        Spreadsheet
(Free tier)   (free tier)   + MISA AMIS/Fast      (internal cost
call sheet,   review/       HÓA ĐƠN ĐIỆN TỬ       sheet giai đoạn
shot list,    approval,     hợp pháp + kế toán    đầu — xem 4.4)
schedule      versioning    thuế VN (bắt buộc)
```

Phân vai rõ ràng — không cố nhét mọi thứ vào một hệ:
- **Odoo Community:** CRM, quotation, project, invoice nội bộ, số liệu quản trị (margin, budget vs actual). KHÔNG dùng làm sổ sách thuế chính thức.
- **MISA/Fast:** hóa đơn điện tử hợp chuẩn (bắt buộc theo NĐ 70/2025/NĐ-CP) + kế toán thuế. Kế toán đối chiếu số với Odoo hàng tháng. Không cần tích hợp API giai đoạn đầu — bridge thủ công (xem Phần 6).
- **StudioBinder/Frame.io:** phần chuyên ngành production/post. Chỉ cần lưu link vào project Odoo tương ứng.
- **Internal cost sheet:** giai đoạn đầu giữ ở Google Sheets/Excel theo template 2 lớp của founder (Odoo Community không mô hình hóa tốt cấu trúc cost bottom-up kiểu AICP). Xem 4.4 về ranh giới Odoo vs Sheet.

## PHẦN 2 — HẠ TẦNG

**VPS tối thiểu** (đủ cho <10 user): 2 vCPU, 4GB RAM, 60GB SSD, Ubuntu 22.04/24.04 LTS. Nhà cung cấp VN (Vietnix, VNG Cloud, Viettel) nếu muốn độ trễ thấp + dữ liệu trong nước, hoặc DigitalOcean/Hetzner (rẻ hơn). Ngân sách ~10–25 USD/tháng.

**Triển khai bằng Docker Compose:** services gồm `odoo` (image chính thức `odoo:18`), `postgres:16`, `nginx` (reverse proxy) hoặc `caddy` (tự động SSL). Điểm cần lưu ý:
- Mount volume cho `odoo-web-data` (filestore) và `postgres-data` — filestore chứa file đính kèm, mất là mất thật.
- Đặt `admin_passwd` (master password) mạnh trong `odoo.conf`; tắt `list_db` sau khi setup xong.
- Chặn truy cập trực tiếp port 8069 từ ngoài; chỉ expose qua reverse proxy HTTPS.
- Bật `proxy_mode = True` trong odoo.conf khi chạy sau nginx.

**Backup (bắt buộc, không thương lượng):**
- `pg_dump` database + tar filestore, hàng đêm, đẩy lên object storage ngoài VPS (Backblaze B2 / S3 / Google Drive qua rclone).
- Giữ 7 bản ngày + 4 bản tuần + 3 bản tháng.
- **Test restore mỗi quý** — backup chưa từng restore thử là backup không tồn tại.

**Bảo trì định kỳ:** update security OS hàng tháng; minor update Odoo mỗi 1–2 tháng (test trên staging DB copy trước); dự trù thực tế ~5–15 giờ/tháng công vận hành. Nếu không có người đảm nhận ổn định, cân nhắc managed hosting Odoo hoặc thuê partner — chi phí đổi lấy thời gian.

## PHẦN 3 — CẤU HÌNH ODOO: MODULES & PIPELINE

**Modules cài đặt (Community, miễn phí):** CRM · Sales · Project · Invoicing · Contacts · (tùy chọn: Timesheets, Documents-community, Email Marketing sau này). KHÔNG cài lan man — mỗi module thêm là chi phí bảo trì thêm.

### 3.1. CRM Pipeline — đúng 10 stage của Playbook

Cấu hình trong CRM > Configuration > Stages:

| # | Stage | Ghi chú cấu hình |
|---|---|---|
| 1 | Lead | Probability mặc định thấp |
| 2 | Qualified / Briefed | Bắt buộc điền Job Type + Tier trước khi kéo sang stage 3 (dùng required field theo stage hoặc automation) |
| 3 | Quoted | Tự động khi tạo quotation từ deal |
| 4 | Won – Deposit | Đánh dấu Won; activity tự động "Thu deposit" |
| 5 | Prep | |
| 6 | Execute | |
| 7 | Post / Review | |
| 8 | Delivered | |
| 9 | Invoiced | |
| 10 | Paid / Wrap | Activity tự động "Cập nhật rate card + actual" |

Lưu ý: stage 5–10 về bản chất là trạng thái *thực thi* — có thể chọn 1 trong 2 cách: (a) giữ cả 10 stage trong CRM cho trực quan một màn hình; hoặc (b) CRM dừng ở Won, các trạm sau tracking bằng Project stages. **Khuyến nghị giai đoạn đầu: cách (a)** — một màn hình duy nhất cho founder, Project chỉ dùng cho task chi tiết của job Tier 2/3.

**Automation tối thiểu (Settings > Technical > Automation Rules):**
- Deal đứng yên >7 ngày ở bất kỳ stage nào (trừ Paid) → tạo activity nhắc người phụ trách. Phục vụ nhịp rà pipeline hàng tuần của founder.
- Deal sang "Won – Deposit" → tạo activity "Gửi hợp đồng + thu deposit", deadline +3 ngày.

### 3.2. Custom fields trên CRM Lead/Opportunity

Tạo qua Settings > Technical > Fields (hoặc module custom nhỏ `ph_core` — khuyến nghị, để field/logic nằm trong code, dễ migrate):

| Field | Kiểu | Giá trị |
|---|---|---|
| `x_job_type` | Selection | event_recap · event_producing · social_video · product_photo · brand_video · tvc · other (danh sách sẽ mở rộng theo founder) |
| `x_tier` | Selection | tier1 · tier2 · tier3 |
| `x_client_kind` | Selection | agency · direct_brand (phục vụ phân tích sau này) |
| `x_positioning` | Selection | cash · bridge · brand (theo khung 70/20/10) |

**Logic gợi ý tier (không bắt buộc code ngay, có thể là hướng dẫn nhập tay):** deal value ≥ ngưỡng 2 → tier3; ≥ ngưỡng 1 → tier2; job_type thuộc nhóm định vị → tier3. Hai ngưỡng tiền do founder chốt, đặt làm system parameter để đổi không cần sửa code.

### 3.3. Custom fields trên Contact (vendor)

| Field | Kiểu | Giá trị |
|---|---|---|
| `x_vendor_kind` | Selection | individual (cá nhân — khấu trừ PIT 10%) · company (hóa đơn VAT) · internal |
| `x_rate_note` | Char/Text | Rate thỏa thuận gần nhất + ghi chú net/gross |

Tag vendor theo vai trò (director, DOP, gaffer, editor, colorist, studio, equipment...) bằng Contact Tags để lọc nhanh khi build cost.

## PHẦN 4 — QUOTATION: SẢN PHẨM, GIÁ, VÀ RANH GIỚI VỚI COST SHEET

### 4.1. Danh mục Products = rate card bán ra

Tạo products kiểu Service cho các hạng mục báo giá, nhóm theo Product Category khớp cấu trúc line items của Playbook: Crew / Cast / Equipment / Location / Art / Logistics / Post / Fees. Ví dụ: "Shooting day – half day", "Editor – per day", "Color grading – per video", "Event recap package – full day".

Bảng giá gói Tier 1 của founder = các product "package" có giá cố định → sales chọn 1 dòng, điền số lượng, xong quote trong 15 phút đúng yêu cầu Playbook.

### 4.2. Cấu trúc quotation gửi client

Trên Sales Order:
- Line items = products đã markup (giá bán).
- **Management fee 10%:** tạo product "Management Fee (10%)" — giai đoạn đầu nhập tay số tiền (10% × subtotal). Nếu muốn tự động: dùng module OCA hoặc automation tính khi confirm. Đừng over-engineer sớm.
- **VAT 8%:** cấu hình Tax 8% mặc định cho các product dịch vụ sản xuất (đang hiệu lực đến 31/12/2026 theo NQ 204/2025 — đặt lịch nhắc cập nhật lại thuế suất trước 01/01/2027).
- **Quotation Templates** (Sales > Configuration): tạo template theo job type, ghi sẵn phần **Assumptions & Exclusions** mặc định + số vòng revision + payment terms trong Terms & Conditions của template. Đây là yêu cầu cứng từ Playbook Phần 3.1 bước 7.

**Payment terms** cấu hình sẵn: "50% deposit – 50% before delivery", "30% – 40% – 30%", Net 15, Net 30.

### 4.3. Margin tracking trên quote

Odoo Sales có sẵn cột **Cost** trên sales order line và margin tính tự động (bật "Margins" trong Settings > Sales). Quy ước vận hành: sau khi chốt internal cost sheet (4.4), nhập **tổng cost thật** vào field cost của các line tương ứng (hoặc 1 line tổng) để Odoo hiển thị margin ngay trên quote — founder nhìn được margin từng deal ngay trong pipeline mà không mở sheet.

### 4.4. Ranh giới Odoo vs Internal Cost Sheet (quan trọng)

Giai đoạn đầu KHÔNG cố build cấu trúc AICP bottom-up (cost từng dòng → %MU từng dòng → gross-up PIT vendor cá nhân → commission → CM) trong Odoo Community — chi phí custom lớn, founder lại đang có sheet chạy tốt. Phân công:

- **Google Sheet/Excel (template 2 lớp của founder):** build cost chi tiết, %MU từng dòng, phân luồng vendor cá nhân (gross-up PIT 10%) vs công ty, commission, margin, CM. Một file mẫu chuẩn, mỗi job copy từ mẫu, đặt tên theo mã deal (xem Phần 5), lưu Drive theo cấu trúc thư mục chuẩn, **dán link vào deal Odoo** (field Internal Notes hoặc custom field `x_costsheet_url`).
- **Odoo:** khung quotation gửi client (số đã chốt từ sheet), tổng cost để tính margin, invoice, pipeline.

Lộ trình sau này (Phase 2–3) mới cân nhắc đưa cost breakdown vào hệ thống (ERPNext hoặc Odoo custom module) khi số job song song đủ lớn để đau.

## PHẦN 5 — QUY ƯỚC DỮ LIỆU & THƯ MỤC

**Mã dự án:** `PH-YYMM-###` (ví dụ PH-2608-042). Dùng làm: tên deal trong CRM (kèm tên client + job type), tên project Odoo, tên file cost sheet, tên thư mục Drive, reference trên invoice. Một mã xuyên suốt = tra cứu 1 phát ra mọi thứ.

**Cấu trúc thư mục chuẩn mỗi dự án (Drive/NAS):**

```
PH-2608-042_ClientName_JobType/
├── 01_Brief_Contract/        (brief, hợp đồng, SOW)
├── 02_Quote_Budget/          (cost sheet, quotation PDF các version)
├── 03_PreProduction/         (script, storyboard, call sheet, casting)
├── 04_Footage/               (theo shoot day; RAW không đụng vào)
├── 05_Post/                  (project files, exports theo version)
├── 06_Deliverables/          (bản final đã approve)
└── 07_Wrap/                  (actual, wrap note, hóa đơn vendor)
```

**Naming version file dựng:** `PH-2608-042_V1_RoughCut`, `_V2_Revised`, `_V3_Final` — khớp quy tắc review 3 vòng. Approval của client luôn gắn theo version cụ thể (trên Frame.io hoặc email).

**Frame.io / StudioBinder:** mỗi job Tier 2/3 tạo project cùng mã; dán link vào deal/project Odoo. Không cần tích hợp API.

## PHẦN 6 — BRIDGE VỚI KẾ TOÁN THUẾ (MISA/FAST)

Không tích hợp API giai đoạn đầu. Quy trình thủ công chuẩn hóa:

1. Odoo invoice (nội bộ) confirm → kế toán xuất **hóa đơn điện tử tương ứng trên MISA meInvoice** (số liệu khớp 100%: line, MF, VAT 8%).
2. Ghi số hóa đơn điện tử ngược lại vào Odoo invoice (field reference) để đối chiếu.
3. Cuối tháng: kế toán đối chiếu doanh thu Odoo ↔ MISA; chi vendor cá nhân đối chiếu chứng từ khấu trừ PIT.
4. Sổ sách thuế chính thức, báo cáo VAT/TNDN/TNCN: **chỉ ở MISA/Fast**. Odoo là số quản trị.

## PHẦN 7 — BÁO CÁO CHO FOUNDER

Dashboard tối thiểu (dùng view/filter có sẵn của Odoo, chưa cần BI tool):

- **Pipeline theo stage** (Kanban CRM, tổng expected revenue mỗi cột) — phục vụ rà tuần.
- **Win/loss theo `x_job_type`** (pivot CRM: stage × job type) — hàng tháng.
- **Doanh thu & margin theo job type và theo `x_positioning`** (pivot Sales Orders: margin × job_type / positioning) — phục vụ review quý 70/20/10 và quyết định tăng giá/bỏ loại job.
- **Invoice quá hạn + DSO** (Invoicing > báo cáo aging có sẵn).
- **Budget vs actual Tier 2/3:** giai đoạn đầu nằm ở cost sheet (cột actual bên cạnh estimate); tổng actual nhập lại vào Odoo (field cost) khi wrap.

Khi outgrow filter/pivot của Odoo → cân nhắc Metabase (open-source) đọc thẳng PostgreSQL read-replica.

## PHẦN 8 — LỘ TRÌNH KỸ THUẬT THEO PHASE

**Phase 1 (tuần 1–4): nền tảng.** VPS + Docker + Odoo + backup chạy được. Cài modules, dựng 10 stage, custom fields (3.2, 3.3), products/rate card v1, quotation templates với assumptions mặc định, payment terms, tax 8%. Import contacts (client + vendor, gắn vendor_kind). Đào tạo team nhập deal.

**Tiêu chí nghiệm thu Phase 1** (khớp thước đo Giai đoạn 1 của Playbook): 100% deal mới nằm trong pipeline; quote Tier 1 tạo được ≤15 phút từ template; backup restore thử thành công 1 lần.

**Phase 2 (tháng 2–3): vận hành sâu.** Automation nhắc deal đứng yên >7 ngày; bật Margins + quy trình nhập cost khi chốt sheet; chuẩn hóa thư mục Drive + mã dự án cho mọi job đang chạy; pivot reports Phần 7; quy trình bridge MISA chạy đều.

**Phase 3 (tháng 4–6+): đánh giá mở rộng.** Timesheets cho job Tier 2/3 (đo giờ công thật theo loại job — dữ liệu cho quyết định bỏ/tăng giá); cân nhắc Metabase; đánh giá pain points của cost-sheet-ngoài-hệ-thống.

**Ngưỡng chuyển stack (từ research):** khi cần kế toán quản trị đầy đủ trong một hệ + đội >10 người + >5 job song song thường xuyên → đánh giá **ERPNext** (accounting đầy đủ miễn phí, quotation→sales order→project→budget vs actual một mạch) hoặc Odoo Enterprise (nếu cần Studio no-code + ngân sách cho phép). Việc migrate nhẹ nhàng nếu ngay từ đầu dữ liệu sạch: mã dự án nhất quán, job_type/tier/vendor_kind đầy đủ, contacts chuẩn.

## PHẦN 9 — CHECKLIST BẢO MẬT & VẬN HÀNH

- [ ] HTTPS toàn bộ, chặn port 8069 trực tiếp, tắt `list_db`, master password mạnh
- [ ] 2FA cho tài khoản admin Odoo; user thường phân quyền theo nhóm (Sales user không thấy margin nếu founder muốn — dùng group "Show margins")
- [ ] Backup đêm + offsite + test restore quý (ghi log lần test)
- [ ] Update OS hàng tháng, Odoo minor 1–2 tháng/lần qua staging
- [ ] Tài liệu hóa: file này + odoo.conf + docker-compose.yml + quy trình restore vào repo riêng (private Git)
- [ ] Nhắc lịch: cập nhật thuế suất VAT trước 01/01/2027; xác nhận ngưỡng PIT vendor cá nhân (2tr→5tr/lần) với kế toán trước khi hard-code vào template
