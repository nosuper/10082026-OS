---
date: 2026-08-10
question: >
  Build-vs-buy for a self-hosted, open-source, AI/MCP-controllable "company OS"
  for a <10-person Vietnamese video production company (Finance, CRM, Quotation,
  Job management, Contracts, Document/invoice organization), running on own infra
  (Proxmox + Synology + reverse proxy) with local AI models.
status: complete
---

# Self-hosted "Agency OS" — build vs buy research

## 1. TL;DR / Recommendation

**Recommended: a composed stack anchored on ERPNext/Frappe, not a from-scratch build and not Odoo.**

- **Core (CRM + Deals + Quotation + Jobs + Accounting): ERPNext on the Frappe Framework.** It is the only fully open-source (GPL-3.0) suite that covers CRM, quotations, projects, and real double-entry accounting in one system with one data model ([github.com/frappe/erpnext](https://github.com/frappe/erpnext)). Critically, its customization story fits the bespoke parts of this workflow: custom DocTypes (tables + forms + REST API + permissions, generated from the UI without code) are exactly the mechanism needed to build the 3-calculator cost breakdown and the ratecard system ([Frappe DocType docs](https://docs.frappe.io/framework/user/en/basics/doctypes)). Multiple community MCP servers already exist for Frappe/ERPNext (none official — see §5), and everything is reachable over the Frappe REST API, so a thin custom MCP server is cheap to build.
- **Documents: Paperless-ngx** (GPL-3.0, Docker Compose, the tool the user already named) for scanned contracts, invoices, receipts — tagged by job code via tags/custom fields; several community MCP servers exist; **paperless-gpt** adds local-LLM (Ollama) OCR/auto-tagging ([github.com/icereed/paperless-gpt](https://github.com/icereed/paperless-gpt)).
- **Signing/contract collection: DocuSeal** (AGPL-3.0, Docker, API + webhooks) for template-based contract generation and signature collection ([github.com/docusealco/docuseal](https://github.com/docusealco/docuseal)).
- **Glue + AI orchestration: n8n** (self-hostable; note it is *fair-code*, not OSI open source — fine for internal use under the Sustainable Use License) — it ships official **MCP Server Trigger** and **MCP Client Tool** nodes, so it can both expose workflows to agents and let agents call other MCP servers ([n8n docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcptrigger/)).
- **Local AI: Ollama** (MIT, Docker) running a Qwen2.5-VL-class vision model (7B fits in ~8–12 GB VRAM quantized) for invoice/receipt extraction and de-brief/quotation drafting.

**Why not the alternatives.** Odoo CE is the closest competitor, but full accounting is Enterprise-only in practice (CE has invoicing + journals; reporting/reconciliation gaps are patched by OCA modules of varying maintenance), and deep customization means writing Odoo addons in Python — a heavier lift than Frappe's UI-defined DocTypes for a 3-person team. Twenty and EspoCRM are CRMs, not company OSes: Twenty has no accounting/quotation at all, and EspoCRM puts quotes/invoices behind the paid Sales Pack. Invoice Ninja is excellent at the quote→invoice→PO slice but is Elastic-licensed (source-available), covers neither CRM pipeline nor job management, and would leave you integrating three more tools anyway. A pure low-code build (NocoDB/Baserow) makes the calculators easy but forces you to rebuild accounting, which is the one thing you should never rebuild.

**The honest caveat:** nothing understands Vietnamese hóa đơn điện tử XML (Decree 123/Circular 78 format) or your 3-calculator costing natively. Those are bespoke in *every* scenario (~2–4 custom DocTypes + one XML parser + one bank-statement importer). ERPNext is the platform where that bespoke work is cheapest and lands inside the same database as your accounting. Expect real setup effort: ERPNext is an ERP, and disabling/hiding the 80% you don't need (manufacturing, stock) is part of the job.

## 2. Requirements recap

| # | Workflow step | Module requirement | Covered by (recommended stack) |
|---|---|---|---|
| 1 | Lead → client record (tax code, bank info) | CRM: companies + contacts, custom fields | ERPNext CRM (Lead/Customer) + custom fields |
| 2 | Brief → Deal → AI de-brief → SOW | Deal/Opportunity + AI text | ERPNext Opportunity + Ollama via MCP/n8n |
| 3 | Cost breakdown (3 calculators) | **Bespoke** line-item costing | Custom Frappe DocTypes (§4.1) |
| 4 | Quotation from ratecards | Quotation + **bespoke** ratecard system | ERPNext Quotation + custom Ratecard DocTypes |
| 5 | Lost (reason) / Won → contract from template → signed copy | Deal stages + doc generation + signing | ERPNext lost-reason field; DocuSeal templates/API |
| 6 | Deal → Job, Kanban/Gantt/Timeline | Project management | ERPNext Projects (Tasks: kanban/list; Gantt) |
| 7 | Expenses via OCR, POs, freelancer contracts, scan signed papers | Expense claims, Purchase Orders, DMS | ERPNext (Expense Claim, PO) + Paperless-ngx + paperless-gpt |
| 8–9 | e-invoices in/out (XML/PDF), AP/AR, payment tracking | Accounting + **bespoke** XML import | ERPNext Accounts + custom hóa đơn điện tử parser (§4.3) |
| 10 | Bank statement import (xlsx/PDF), reconciliation, reporting | Bank rec + reports | ERPNext Bank Reconciliation + import script (§4.4) |
| 11 | Everything organized by job code | DMS with tags/custom fields + API | Paperless-ngx (tags, custom fields, storage paths) |

## 3. Candidate-by-candidate findings

### 3.1 ERPNext / Frappe Framework — **recommended core**

- **Covers:** Accounting (double-entry, AP/AR, reports), CRM & Sales (customers/suppliers, leads, opportunities, quotations), Project Management (tasks, timesheets, issues), plus order management/assets you can ignore. Source: [github.com/frappe/erpnext](https://github.com/frappe/erpnext) README.
- **License:** GPL-3.0 ([repo](https://github.com/frappe/erpnext)).
- **Customization:** Built on Frappe Framework. A **DocType** defines data model + form + list view and auto-creates the DB table; new DocTypes can be created from the UI without code ([docs.frappe.io DocType docs](https://docs.frappe.io/framework/user/en/basics/doctypes)). Frappe provides "a database abstraction layer, user authentication, and a REST API" ([erpnext README](https://github.com/frappe/erpnext)) — every DocType, including custom ones, is automatically API-accessible. This is the key differentiator for the bespoke costing work.
- **Self-host:** Official Docker route via [frappe/frappe_docker](https://github.com/frappe/frappe_docker) (Docker Compose v2); manual `bench` install also documented ([erpnext README](https://github.com/frappe/erpnext)).
- **Vietnam localization:** ERPNext ships country-wise Charts of Accounts in local languages ([erpnext wiki: Country-wise CoA](https://github.com/frappe/erpnext/wiki/Country-wise-Chart-of-Accounts)) and a Chart of Accounts Importer for bringing your own ([docs](https://docs.frappe.io/erpnext/chart-of-accounts-importer)). Whether a maintained Vietnam (Circular 200) CoA is bundled was **not verified** — plan to import the accountant's CoA via the importer regardless (secondary — verify). VAT/PIT per line item is modeled with ERPNext's item-wise tax templates plus custom fields; no Vietnam e-invoice (TCT) integration exists — that's custom (§4.3).
- **MCP status:** No official Frappe MCP server found. Active community options (all unofficial): [buildswithpaul/Frappe_Assistant_Core](https://github.com/buildswithpaul/Frappe_Assistant_Core) (installs as a Frappe app, exposes ERPNext over MCP), [Casys-AI/mcp-erpnext](https://github.com/Casys-AI/mcp-erpnext) (~120 tools), [rakeshgangwar/erpnext-mcp-server](https://github.com/rakeshgangwar/erpnext-mcp-server), [mascor/frappe-mcp-server](https://github.com/mascor/frappe-mcp-server) (permissions + audit logging). Maturity of each **not verified in depth** — evaluate Frappe_Assistant_Core first (runs inside Frappe, so it inherits Frappe permissions), and be ready to build a thin custom MCP server over the REST API instead.

### 3.2 Odoo Community Edition — viable runner-up, heavier customization

- **Covers (CE):** CRM, Project Management, "Billing & Accounting", Website, etc. ([github.com/odoo/odoo](https://github.com/odoo/odoo) README).
- **The accounting catch:** the full Accounting app is Enterprise; CE can post customer invoices, vendor bills, payments and journal entries, but lacks Enterprise's financial reports, bank sync, and automated reconciliation — gaps traditionally filled by OCA add-ons ([OCA discussion #181](https://github.com/orgs/OCA/discussions/181), [Odoo forum: Accounting Community vs Enterprise](https://www.odoo.com/forum/help-1/accounting-community-vs-enterprise-271286)) (partly secondary — verify against your Odoo version).
- **License:** CE is LGPL-3 per the repo LICENSE ([github.com/odoo/odoo/blob/master/LICENSE](https://github.com/odoo/odoo/blob/master/LICENSE)) (license file not read directly — verify).
- **Customization:** real Python addon development (models/views/inheritance); more powerful, materially more effort than Frappe DocTypes for a small team. External API is XML-RPC/JSON-RPC ([odoo.com developer docs](https://www.odoo.com/documentation/18.0/developer/reference/external_api.html)) (not fetched — verify).
- **MCP status:** no single official server, but a busy ecosystem including Odoo Apps Store modules that embed an MCP endpoint in Odoo itself ([mcp_server 17.0](https://apps.odoo.com/apps/modules/17.0/mcp_server), [mn_mcp_server 19.0](https://apps.odoo.com/apps/modules/19.0/mn_mcp_server), [MuK MCP 19.0](https://apps.odoo.com/apps/modules/19.0/muk_mcp)) and standalone [ivnvxd/mcp-server-odoo](https://github.com/ivnvxd/mcp-server-odoo). All community/vendor, none from Odoo S.A. — maturity **not verified**.

### 3.3 Twenty CRM — good CRM, wrong scope

Open-source "alternative to Salesforce, designed for AI": custom objects/fields, kanban views, workflows, AI agents; GraphQL (and REST) API; Docker Compose self-hosting; TypeScript/NestJS/PostgreSQL ([github.com/twentyhq/twenty](https://github.com/twentyhq/twenty)). No accounting, quotation, or project module — it would cover only step 1–2 of the workflow. No official MCP server confirmed; multiple community ones exist (e.g. [mhenry3164/twenty-crm-mcp-server](https://github.com/mhenry3164/twenty-crm-mcp-server) — unofficial). Not recommended here: it would still need everything else bolted on.

### 3.4 EspoCRM — quotes are behind a paywall

Free core: leads, opportunities, accounts/contacts, email, documents, entity manager + formula customization, REST API. But **"Quotation and invoicing, Purchases, Payments" require the paid Sales Pack**, and Workflows/BPM require the paid Advanced Pack ([espocrm.com/features](https://www.espocrm.com/features/)). Core is AGPL-3.0 ([github.com/espocrm/espocrm](https://github.com/espocrm/espocrm)) (license from repo listing — verify). Since quotation is a core requirement, EspoCRM free doesn't fit; with paid packs it still lacks accounting and real project management. SuiteCRM/Krayin not investigated further — same scope problem (CRM-only).

### 3.5 Invoice Ninja — best-in-class slice, license caveat

Self-hosted covers invoices, quotes, expenses, projects/time-tracking, with vendors and purchase orders in the system; full API with docs; official Docker image; all hosted Pro/Enterprise features included when self-hosting; **Elastic License (source-available, not OSI open source)**; optional $40/yr white-label to remove branding ([invoiceninja.github.io](https://invoiceninja.github.io/)). E-invoicing support (EU/PEPPOL-oriented) exists in v5 but was **not verified for scope**, and it will not cover Vietnamese hóa đơn điện tử. Verdict: fine as a standalone quoting/AP tool, but in this stack ERPNext already does quotes/POs/expenses inside the accounting ledger, so Invoice Ninja adds a second source of truth. Skip unless ERPNext quoting UX proves too heavy.

### 3.6 Paperless-ngx — **recommended DMS**

"Document management system that transforms your physical documents into a searchable online archive" (OCR ingest); tags, correspondents, document types, storage paths; GPL-3.0; official Docker Compose deployment ([github.com/paperless-ngx/paperless-ngx](https://github.com/paperless-ngx/paperless-ngx)). Custom fields and a full REST API are documented at [docs.paperless-ngx.com](https://docs.paperless-ngx.com/) (docs site blocked automated fetch — API details from repo/ecosystem; verify the custom-fields filtering syntax there). Job-code mapping: use a `job_code` custom field + per-job tags + storage-path templates. **MCP:** no official server; the maintainers' discussion board hosts a community MCP project thread ([discussion #9958](https://github.com/paperless-ngx/paperless-ngx/discussions/9958)); notable community servers: [cubinet-code/paperless-ngx-mcp](https://github.com/cubinet-code/paperless-ngx-mcp) (covers documents, tags, custom fields, storage paths, workflows, tasks), [baruchiro/paperless-mcp](https://github.com/baruchiro/paperless-mcp), [nloui/paperless-mcp](https://github.com/nloui/paperless-mcp). Maturity **not verified** — cubinet-code's looks broadest on paper.

### 3.7 DocuSeal — **recommended for contracts/signing**

Open-source document signing: PDF form/template builder, 12 field types, multiple submitters, SMTP automation, PDF eSignature + verification, **API and webhooks in the free tier**; AGPL-3.0 (with §7(b) additional terms); one-container Docker deploy, SQLite default or PostgreSQL/MySQL. Pro (paid) adds white-label, roles, SMS verification, conditional fields, bulk send, SSO, embedded components, and **template creation via HTML/PDF API** ([github.com/docusealco/docuseal](https://github.com/docusealco/docuseal)). Note: if auto-generating contracts from templates via API is core to your flow, check which template-API endpoints sit in Pro before committing. No MCP server found (not verified to exist); the REST API is simple enough that an n8n workflow or tiny MCP wrapper suffices. Legal note: Vietnamese contract signing practice often still requires wet-ink/company-seal copies — DocuSeal handles the generate-and-track loop; the signed-paper scan still lands in Paperless-ngx.

### 3.8 Firefly III — wrong fit, excluded

Explicitly **personal** finance ("for people who want to track their finances… keep an eye on their money"), AGPL-3.0, strong REST API, Docker image, separate Data Importer tool ([github.com/firefly-iii/firefly-iii](https://github.com/firefly-iii/firefly-iii)). No invoicing, no AP/AR ledgers per counterparty in a business sense. Do not use for company books; ERPNext accounting replaces it entirely.

### 3.9 n8n — glue layer, license caveat

Self-hostable workflow automation with native AI/LangChain nodes. **License: Sustainable Use License (fair-code)** — free for internal business use; restrictions apply to redistribution/commercial resale; n8n itself does not call it open source ([docs.n8n.io/sustainable-use-license](https://docs.n8n.io/sustainable-use-license/), [LICENSE.md](https://github.com/n8n-io/n8n/blob/master/LICENSE.md)). Internal use at a production company is squarely permitted. **MCP, verified in official docs:** the **MCP Server Trigger** node makes n8n act as an MCP server exposing workflows/tools to external MCP clients (SSE + Streamable HTTP transports; bearer/header auth) ([docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcptrigger/)), and the **MCP Client Tool** node lets n8n agents consume external MCP servers (bearer/header/OAuth2 auth) ([docs](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolmcp/)). This makes n8n the natural place for: e-invoice XML ingestion, bank-statement parsing pipeline, DocuSeal webhooks → ERPNext status updates, Paperless→ERPNext expense drafts.

### 3.10 Low-code builders (NocoDB / Baserow / Appsmith / Budibase) — brief

- **NocoDB**: official, built-in MCP endpoints documented at [nocodb.com/docs/product-docs/mcp](https://nocodb.com/docs/product-docs/mcp) — LLMs get secure per-endpoint URLs for CRUD.
- **Baserow**: official embedded MCP server, documented at [baserow.io/user-docs/mcp](https://baserow.io/user-docs/mcp).
- Both are credible platforms for the *calculator/ratecard* tables if you wanted them outside ERPNext — but that splits costing data from accounting. Appsmith/Budibase (app builders) not investigated in depth; only relevant if you want custom calculator UIs over ERPNext's API later. Verdict: not needed in v1; Frappe DocTypes do this in-suite.

## 4. The bespoke parts (custom in every scenario)

### 4.1 Three-calculator cost breakdown — build as Frappe DocTypes
No off-the-shelf tool models "2-unit pricing + VAT/PIT per line + vendor management fee % + internal gross" or "commission % / consolidated margin per line" or "management fee + markup − discount + 8% VAT quote price". In ERPNext: one custom child DocType `Cost Line` (fields: item, 2 unit quantities, unit price, VAT %, PIT %, mgmt fee %, computed internal gross / margin / quote price) attached to Opportunity/Quotation, with computed fields via client scripts or server-side hooks. DocTypes are UI-definable and instantly get forms, list views, permissions, and REST endpoints ([Frappe DocType docs](https://docs.frappe.io/framework/user/en/basics/doctypes)). Estimate: the largest single custom item, but bounded — it's arithmetic over a child table.

### 4.2 Ratecard system — Frappe DocTypes + ERPNext Price Lists
ERPNext natively has Items and per-party Price Lists (selling/buying), which cover "client ratecard" and "vendor/freelancer buying rates" to a first approximation; a custom `Ratecard` DocType wrapping Price List with validity dates and role rates fills the rest. AI-assisted quotation = agent reads ratecards via MCP, drafts Quotation lines, human refines in the ERPNext UI.

### 4.3 Vietnam e-invoice (hóa đơn điện tử) XML import — custom parser
Legal basis: e-invoices are XML per Article 12 of Decree 123/2020/NĐ-CP, implemented by Circular 78/2021/TT-BTC; the mandatory XML data-format standard is defined by GDT Decisions 1450/QĐ-TCT (2021) and 1510/QĐ-TCT (2022); note **Circular 32/2025/TT-BTC has superseded Circular 78** as current guidance (regulatory summaries: [vatcompliance.co Vietnam guide](https://vatcompliance.co/guides/e-invocing/vietnam/), [Pagero/Thomson Reuters Vietnam compliance](https://www.pagero.com/compliance/regulatory-updates/vietnam) — secondary sources; the Decisions themselves are the primary schema source — verify against 1450/1510 text). **None of the candidate tools parse this format natively** (no evidence found anywhere). Build: a small Python parser (the schema is stable, fields like seller/buyer MST, line items, VAT rate, invoice serial/number are well-defined XML elements) run as an n8n workflow or Frappe server script that creates ERPNext Purchase Invoices / attaches to Sales Invoices, and files the XML+PDF pair into Paperless-ngx under the job code. This is a few days of work, not a project.

### 4.4 Bank statement import (xlsx/PDF) — importer + ERPNext bank reconciliation
Vietnamese banks export xlsx (varies per bank) — write one n8n/Python normalizer per bank into ERPNext Bank Transaction records, then use ERPNext's built-in bank reconciliation. PDF statements: run through the vision model (§5) as fallback. Firefly III's importer is CSV/CAMT-oriented and points at the wrong ledger anyway.

### 4.5 De-brief → SOW, quotation drafting — prompt work, not platform work
Lives in n8n (AI nodes + Ollama) or a Claude-style MCP client talking to the ERPNext MCP server. No custom platform code beyond prompts and one or two n8n workflows.

## 5. AI/MCP integration plan

**MCP fundamentals:** MCP is an open standard for connecting AI apps to external systems — servers expose tools/resources/prompts to clients over stdio or streamable HTTP; official SDKs in multiple languages ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/getting-started/intro)). Building a custom server over a clean REST API (which every recommended tool has) is a small task.

**Exists today (all community/unofficial unless noted):**
| System | MCP today | Notes |
|---|---|---|
| ERPNext/Frappe | Community: [Frappe_Assistant_Core](https://github.com/buildswithpaul/Frappe_Assistant_Core), [Casys-AI/mcp-erpnext](https://github.com/Casys-AI/mcp-erpnext), others | No official server; maturity unverified — trial before trusting writes |
| Paperless-ngx | Community: [cubinet-code/paperless-ngx-mcp](https://github.com/cubinet-code/paperless-ngx-mcp), [baruchiro/paperless-mcp](https://github.com/baruchiro/paperless-mcp) | No official server; feature request open upstream ([#10372](https://github.com/paperless-ngx/paperless-ngx/discussions/10372)) |
| n8n | **Official** MCP Server Trigger + MCP Client Tool nodes ([docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcptrigger/)) | Verified in official docs; the safest MCP surface in the stack |
| DocuSeal | None found | Wrap its REST API via n8n MCP Server Trigger or a ~200-line custom server |
| NocoDB / Baserow | **Official**, built-in ([NocoDB](https://nocodb.com/docs/product-docs/mcp), [Baserow](https://baserow.io/user-docs/mcp)) | Only relevant if adopted |

**Must be built:** (1) hardened ERPNext MCP server if community options disappoint — scope it to the DocTypes agents actually need (Lead, Opportunity, Cost Line, Quotation, Project/Task, Purchase Invoice) with per-tool write gating; (2) DocuSeal wrapper; (3) e-invoice + bank-statement ingestion tools (exposed as n8n workflows behind the MCP Server Trigger).

**Local models (on Proxmox — needs a GPU passthrough VM):**
- **Ollama** (MIT, Docker image `ollama/ollama`, REST API at :11434) as the serving layer ([github.com/ollama/ollama](https://github.com/ollama/ollama)); vLLM only if batch throughput ever matters — overkill at this team size.
- **Vision/OCR:** Qwen2.5-VL-7B runs on a single ~12 GB GPU at 4-bit and does structured JSON extraction from invoices (community benchmarks: ~20–30 tok/s on an RTX 3090 at Q4_K_M) (secondary — verify on your hardware; sources: [labellerr guide](https://www.labellerr.com/blog/run-qwen2-5-vl-locally/), [localaimaster](https://localaimaster.com/blog/local-ai-vision-tasks)). Division of labor: Paperless-ngx's built-in OCR (tesseract-based) handles searchable-text ingest; **[paperless-gpt](https://github.com/icereed/paperless-gpt)** (MIT, Docker) adds LLM/vision OCR + auto title/tag/correspondent against an Ollama backend — this is the highest-leverage, lowest-effort AI win in the stack.
- **Text (de-brief, SOW, quotation drafts):** any strong local instruct model via Ollama; Vietnamese quality matters — test Qwen-family first (strong multilingual) (opinion, not benchmarked).

## 6. Open questions (need user decision or a prototype)

1. **ERPNext UX tolerance:** will Linh/Vu accept ERPNext's dense UI for daily deal/quote work, or is a simplified custom front-end (Frappe UI page or Appsmith over the API) needed? → 2-week pilot with one real job.
2. **Vietnam CoA + tax setup:** get the external accountant's chart of accounts and VAT/PIT treatment (esp. freelancer PIT withholding 10%?) and load via the CoA Importer — confirms whether ERPNext accounting is kept authoritative or stays "management accounting" alongside the accountant's books. This decision changes how much accounting rigor you need.
3. **Which ERPNext MCP server:** trial Frappe_Assistant_Core vs Casys-AI vs building thin custom — decide after testing write-safety and permission behavior.
4. **DocuSeal free vs Pro:** verify the template-creation-via-API endpoints needed for auto-generated contracts are in the free tier; also confirm e-signature legal standing for your contract types in Vietnam vs wet-ink+seal practice.
5. **GPU:** what GPU can go in the Proxmox node? <12 GB VRAM constrains vision-model choice; no GPU means CPU-only OCR (slow) or a cloud-API compromise.
6. **Circular 32/2025/TT-BTC:** confirm with the accountant what changed vs Circular 78 for invoice format/handling before writing the XML parser.
7. **Backup topology:** ERPNext (MariaDB) + Paperless (media) + DocuSeal volumes → Synology NAS via scheduled dumps/snapshots; decide RPO. All recommended tools have official Docker Compose deployments ([frappe_docker](https://github.com/frappe/frappe_docker), [paperless-ngx](https://github.com/paperless-ngx/paperless-ngx), [docuseal](https://github.com/docusealco/docuseal), [n8n](https://docs.n8n.io/hosting/), [ollama](https://github.com/ollama/ollama)); the whole stack minus GPU inference fits comfortably in 2 VMs / ~8–12 GB RAM (estimate, not benchmarked).
