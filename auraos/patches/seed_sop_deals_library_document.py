"""The deal-classification SOP becomes the first Library document (#66).

Until now this SOP was a Vue template, `frontend/src/pages/SopDealsPage.vue`,
and editing a sentence in it meant a deploy. It moves here so the founder
can edit it in the app - which is the whole point of the Library half of
the Documents screen, and which also unblocks #103, since this page was
the last Vue route with no React counterpart.

**One deliberate change of meaning, and it is not a transcription slip.**
The Vue page did not state the positioning mix as text: it fetched
`auraos.api.classification_hints` and interpolated the live
cash/bridge/brand targets in two places - the Bước 1 paragraph and the
closing quarterly-rhythm sentence. The author's own comment said why:

    Live targets, not hard-coded 70/20/10: the founder tunes these per
    business phase and this page must keep telling the truth.

A Library document is static HTML by design - no placeholders, no
per-job generation, that is Paperwork's job. Transcribing the numbers as
they read today would have produced a document that says 70/20/10,
looks right, and turns into a lie the first time the mix is retuned in
Settings, with nothing on screen marking it stale. Since
`positioning_mix()` falls back to 70/20/10 whenever the setting is unset
or 0, that seed would have looked correct on the day it ran no matter
what the site was actually configured for.

So **both** interpolations were replaced with a pointer to Settings
rather than a figure. The document no longer tells you the mix; it tells
you where the mix lives. The founder chose this over the alternatives
(a live strip above the body, or a placeholder token) for the reason
that it is the only one where the document cannot ever be stale, because
it does not state a number.

The tier thresholds needed nothing - the author had already written
those as "ngưỡng trên/dưới ... chỉnh trong Settings" rather than baking
50/200 into the prose.

**Re-runnable.** Keyed off the document's title: if one is already on
file the patch does nothing, so a second run never restores this text
over an edit the founder has since made. That matters more here than on
most patches - the whole feature is that this text is editable now.
"""

import frappe

CATEGORY = "SOP"

TITLE = "SOP - Đánh giá & phân loại deal"

BODY = """\
<p>Rút từ Playbook §2.2 (tier), §6.1 (positioning). Trả lời đúng một câu hỏi; \
phần còn lại hệ thống tự xếp.</p>

<h2>Bước 1 - Positioning: job này với công ty là gì?</h2>
<p>Câu hỏi chiến lược duy nhất, chỉ founder trả lời. Mục tiêu phân bổ hiện tại \
xem trong <b>Settings &gt; Định vị</b> - chỉnh theo phase của công ty.</p>
<ul>
<li><b>Cash</b> - Nuôi bộ máy. Điều kiện duy nhất: margin dương, không phá giá \
thị trường của chính mình. Ví dụ: recap sự kiện, chụp sản phẩm.</li>
<li><b>Bridge</b> - Job cơm áo có yếu tố gần định vị - recap cho brand lớn, \
social video được tự do sáng tạo. Chăm kỹ nhất: đây là cầu nối lên Brand.</li>
<li><b>Brand</b> - Thứ công ty MUỐN được thuê để làm - TVC, brand film, passion \
project. Đây là portfolio kéo Tier 3 về.</li>
</ul>

<h2>Bước 2 - Tier: hệ thống tự xếp</h2>
<ol>
<li>Positioning là <b>Brand</b>, hoặc loại job được gắn cờ "định vị" trong \
Settings → <b>Tier 3</b> bất kể giá trị.</li>
<li>Còn lại xếp theo budget dự kiến: đạt ngưỡng trên → <b>Tier 3</b>, đạt ngưỡng \
dưới → <b>Tier 2</b>, dưới nữa → <b>Tier 1</b> (hai ngưỡng chỉnh trong Settings).</li>
</ol>
<p>Pin tay khi biết điều hệ thống không thấy: ≥2 ngày quay → tối thiểu Tier 2; \
có cast/talent chuyên nghiệp hoặc nhiều location → Tier 3. Sửa cột Tier trong \
bảng deals để pin; xóa ô đó để trả về tự động.</p>

<h2>Tier quyết định độ dày quy trình</h2>
<table>
<thead>
<tr><th>Trạm</th><th>Tier 1</th><th>Tier 2</th><th>Tier 3</th></tr>
</thead>
<tbody>
<tr><td>Quote</td><td>Bảng giá gói, ≤15 phút</td><td>Breakdown theo nhóm</td>\
<td>Full bid line-by-line + treatment</td></tr>
<tr><td>Prep</td><td>Checklist 1 trang</td><td>Checklist + lịch + phân công</td>\
<td>Call sheet, shot list, storyboard sign-off</td></tr>
<tr><td>Review</td><td>1-2 vòng</td><td>2 vòng có cấu trúc</td>\
<td>3 vòng chuẩn, versioning đầy đủ</td></tr>
<tr><td>Wrap</td><td>Ghi tổng giờ công</td><td>Budget vs actual theo nhóm</td>\
<td>Actualization từng line + wrap report</td></tr>
</tbody>
</table>

<p>Nhịp quý: đo margin theo loại job, so tỷ trọng thực tế với mục tiêu phân bổ \
trong <b>Settings &gt; Định vị</b>, rồi chỉnh các thông số trong Settings - \
không chỉnh bằng trí nhớ.</p>"""


def execute():
    if frappe.db.exists("Library Document", {"title": TITLE}):
        return

    if not frappe.db.exists("Library Category", CATEGORY):
        frappe.get_doc({"doctype": "Library Category", "category_name": CATEGORY}).insert(
            ignore_permissions=True
        )

    frappe.get_doc(
        {
            "doctype": "Library Document",
            "title": TITLE,
            "category": CATEGORY,
            "body": BODY,
        }
    ).insert(ignore_permissions=True)
