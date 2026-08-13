<template>
  <div class="mx-auto max-w-2xl px-4 py-6">
    <h1 class="text-lg font-semibold text-gray-900">
      SOP - Đánh giá &amp; phân loại deal
    </h1>
    <p class="mt-1 text-xs text-gray-500">
      Rút từ Playbook §2.2 (tier), §6.1 (positioning). Trả lời đúng một câu
      hỏi; phần còn lại hệ thống tự xếp.
    </p>

    <div class="mt-5 rounded-lg border bg-white p-4">
      <h2 class="text-sm font-semibold text-gray-800">
        Bước 1 - Positioning: job này với công ty là gì?
      </h2>
      <p class="mt-1 text-xs text-gray-500">
        Câu hỏi chiến lược duy nhất, chỉ founder trả lời. Mục tiêu phân bổ
        hiện tại: Cash ~{{ mix.cash }}% · Bridge ~{{ mix.bridge }}% · Brand
        ~{{ mix.brand }}% (chỉnh trong Settings theo phase của công ty).
      </p>
      <div class="mt-3 space-y-3 text-sm">
        <div class="flex gap-3">
          <span class="mt-0.5 h-fit shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">Cash</span>
          <p class="text-gray-700">
            Nuôi bộ máy. Điều kiện duy nhất: margin dương, không phá giá thị
            trường của chính mình. Ví dụ: recap sự kiện, chụp sản phẩm.
          </p>
        </div>
        <div class="flex gap-3">
          <span class="mt-0.5 h-fit shrink-0 rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700">Bridge</span>
          <p class="text-gray-700">
            Job cơm áo có yếu tố gần định vị - recap cho brand lớn, social
            video được tự do sáng tạo. Chăm kỹ nhất: đây là cầu nối lên
            Brand.
          </p>
        </div>
        <div class="flex gap-3">
          <span class="mt-0.5 h-fit shrink-0 rounded-full bg-violet-50 px-2 py-0.5 text-xs font-medium text-violet-700">Brand</span>
          <p class="text-gray-700">
            Thứ công ty MUỐN được thuê để làm - TVC, brand film, passion
            project. Đây là portfolio kéo Tier 3 về.
          </p>
        </div>
      </div>
    </div>

    <div class="mt-4 rounded-lg border bg-white p-4">
      <h2 class="text-sm font-semibold text-gray-800">
        Bước 2 - Tier: hệ thống tự xếp
      </h2>
      <ol class="mt-2 list-decimal space-y-1.5 pl-5 text-sm text-gray-700">
        <li>
          Positioning là <span class="font-medium">Brand</span>, hoặc loại
          job được gắn cờ "định vị" trong Settings →
          <span class="font-medium text-violet-700">Tier 3</span> bất kể
          giá trị.
        </li>
        <li>
          Còn lại xếp theo budget dự kiến: đạt ngưỡng trên →
          <span class="font-medium text-violet-700">Tier 3</span>, đạt
          ngưỡng dưới → <span class="font-medium text-blue-700">Tier 2</span>,
          dưới nữa → <span class="font-medium">Tier 1</span> (hai ngưỡng
          chỉnh trong Settings).
        </li>
      </ol>
      <p class="mt-2 text-xs text-gray-500">
        Pin tay khi biết điều hệ thống không thấy: ≥2 ngày quay → tối thiểu
        Tier 2; có cast/talent chuyên nghiệp hoặc nhiều location → Tier 3.
        Sửa cột Tier trong bảng deals để pin; xóa ô đó để trả về tự động.
      </p>
    </div>

    <div class="mt-4 rounded-lg border bg-white p-4">
      <h2 class="text-sm font-semibold text-gray-800">
        Tier quyết định độ dày quy trình
      </h2>
      <div class="mt-2 overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead>
            <tr class="border-b text-xs text-gray-500">
              <th class="py-1.5 pr-3 font-medium">Trạm</th>
              <th class="py-1.5 pr-3 font-medium">Tier 1</th>
              <th class="py-1.5 pr-3 font-medium">Tier 2</th>
              <th class="py-1.5 font-medium">Tier 3</th>
            </tr>
          </thead>
          <tbody class="text-gray-700">
            <tr class="border-b">
              <td class="py-1.5 pr-3 text-gray-500">Quote</td>
              <td class="py-1.5 pr-3">Bảng giá gói, ≤15 phút</td>
              <td class="py-1.5 pr-3">Breakdown theo nhóm</td>
              <td class="py-1.5">Full bid line-by-line + treatment</td>
            </tr>
            <tr class="border-b">
              <td class="py-1.5 pr-3 text-gray-500">Prep</td>
              <td class="py-1.5 pr-3">Checklist 1 trang</td>
              <td class="py-1.5 pr-3">Checklist + lịch + phân công</td>
              <td class="py-1.5">Call sheet, shot list, storyboard sign-off</td>
            </tr>
            <tr class="border-b">
              <td class="py-1.5 pr-3 text-gray-500">Review</td>
              <td class="py-1.5 pr-3">1-2 vòng</td>
              <td class="py-1.5 pr-3">2 vòng có cấu trúc</td>
              <td class="py-1.5">3 vòng chuẩn, versioning đầy đủ</td>
            </tr>
            <tr>
              <td class="py-1.5 pr-3 text-gray-500">Wrap</td>
              <td class="py-1.5 pr-3">Ghi tổng giờ công</td>
              <td class="py-1.5 pr-3">Budget vs actual theo nhóm</td>
              <td class="py-1.5">Actualization từng line + wrap report</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <p class="mt-4 text-xs text-gray-400">
      Nhịp quý: đo margin theo loại job, so tỷ trọng thực tế với mục tiêu
      {{ mix.cash }}/{{ mix.bridge }}/{{ mix.brand }}, rồi chỉnh các thông
      số trong Settings - không chỉnh bằng trí nhớ.
    </p>
  </div>
</template>

<script setup>
import { reactive } from "vue"
import { createResource } from "frappe-ui"

// Live targets, not hard-coded 70/20/10: the founder tunes these per
// business phase and this page must keep telling the truth.
const mix = reactive({ cash: 70, bridge: 20, brand: 10 })

createResource({
  url: "auraos.api.classification_hints",
  auto: true,
  onSuccess(value) {
    Object.assign(mix, value)
  },
})
</script>
