# Runbook: khôi phục AuraOS từ số không

> **In tài liệu này ra giấy, hoặc lưu một bản ngoài máy chủ (điện thoại, Drive, USB).**
> Một quy trình khôi phục nằm bên trong thứ vừa chết là tờ giấy khoá trong xe.
> Ngày cần tới nó, anh sẽ không mở được repo này.

Tài liệu này dành cho người đang gấp và không phải người viết ra hệ thống.
Mỗi bước có: **lệnh chạy**, **dấu hiệu thành công**, và **làm gì nếu hỏng**.

---

## 0. Thời gian dự kiến: CHƯA BIẾT

Chưa có ai bấm giờ một lần khôi phục thật.

> **Điền sau lần diễn tập đầu tiên:**
> Ngày diễn tập: `____________`
> Tổng thời gian: `____________`
> Bước lâu nhất: `____________`

Không đoán con số ở đây. Một con số đoán bừa sẽ khiến người đọc tưởng mình
đang chậm bất thường, rồi bỏ giữa chừng để đi làm cách khác.

---

## 1. Trước khi bắt đầu, cần có đủ ba thứ

| Thứ cần | Ở đâu | Nếu thiếu |
|---|---|---|
| Quyền vào máy chủ (ssh/console) | Nhà cung cấp VPS | Không làm tiếp được. Lấy quyền trước. |
| File sao lưu `auraos-*.tar` | `/var/backups/auraos` trên máy chủ, và bản offsite trên NAS | Xem bước 2 |
| **Mật khẩu trong `docker/.env.prod`** | **Password manager của anh** | Xem cảnh báo ngay dưới |

> **Cảnh báo quan trọng: file `docker/.env.prod` KHÔNG nằm trong bản sao lưu.**
> Nó chứa mật khẩu database và mật khẩu Administrator, không bao giờ được commit
> vào git và không được đóng gói cùng archive. Nếu máy chủ mất và anh không có
> hai mật khẩu đó, dữ liệu vẫn khôi phục được nhưng phải tạo mật khẩu mới bằng
> `scripts/wizard-production.sh`, và mọi tài liệu ghi mật khẩu cũ sẽ sai.
>
> **Lưu hai mật khẩu đó vào password manager ngay hôm nay nếu chưa làm.**

---

## 2. Tìm bản sao lưu mới nhất

```bash
ls -lt /var/backups/auraos/auraos-*.tar | head -5
tail -20 /var/backups/auraos/backup.log
```

**Thành công:** thấy ít nhất một file `.tar`, và dòng cuối của log là `OK`.

**Nếu thư mục trống hoặc máy chủ đã mất:** lấy bản offsite trên NAS
(đường dẫn trong `AURA_BACKUP_OFFSITE` của cron). Copy về máy mới rồi tiếp tục.

**Nếu file mới nhất quá cũ:** vẫn dùng nó. Một bản cũ ba ngày là dữ liệu mất ba
ngày; không có bản nào là mất tất cả. Ghi lại ngày của file để biết cần nhập
tay lại những gì.

---

## 3. Dựng stack (chỉ khi máy chủ là máy mới)

Nếu máy chủ cũ vẫn sống và chỉ site hỏng, **bỏ qua bước này**, sang bước 4.

```bash
git clone <repo> /opt/auraos
cd /opt/auraos
scripts/wizard-production.sh        # hỏi domain, port, mật khẩu; ghi docker/.env.prod
```

**Thành công:** wizard in ra `Wrote docker/.env.prod` và stack trả lời `ping`.

**Nếu wizard báo `.env.prod already exists`:** file cũ vẫn còn, dùng lại nó,
đừng xoá. Mật khẩu trong đó phải khớp với database sắp khôi phục.

---

## 4. Khôi phục dữ liệu

Trong ví dụ dưới, thay `<archive>` bằng đường dẫn file `.tar` ở bước 2, và
`<site>` bằng tên site trong `.env.prod` (`AURA_SITE`).

```bash
# 4.1 - đưa archive vào trong container và bung ra
docker exec aura-prod-frappe-1 mkdir -p /tmp/restore
docker exec -i aura-prod-frappe-1 tar -xf - -C /tmp/restore < <archive>
docker exec aura-prod-frappe-1 ls /tmp/restore

# 4.2 - khôi phục (lệnh này GHI ĐÈ site hiện tại)
docker exec aura-prod-frappe-1 bash -lc \
  "cd /home/frappe/frappe-bench && bench --site <site> --force restore \
     /tmp/restore/*-database.sql.gz \
     --with-public-files /tmp/restore/*-files.tar \
     --with-private-files /tmp/restore/*-private-files.tar \
     --db-root-password '<AURA_DB_ROOT_PW>'"

# 4.3 - dọn
docker exec aura-prod-frappe-1 rm -rf /tmp/restore
```

**Thành công ở 4.1:** `ls` liệt kê ba file: `-database.sql.gz`, `-files.tar`,
`-private-files.tar`.

**Thành công ở 4.2:** lệnh kết thúc không báo lỗi. Chưa tin vội, bước 5 mới là
chỗ xác nhận.

**Nếu 4.2 báo sai mật khẩu:** mật khẩu phải lấy từ `docker/.env.prod`
(`AURA_DB_ROOT_PW`), không phải mật khẩu Administrator.

**Nếu 4.2 báo thiếu file private:** một số bản sao lưu không có file private nếu
site chưa có tệp đính kèm nào. Bỏ tham số `--with-private-files` rồi chạy lại.

---

## 5. Xác nhận đã khôi phục thật

Đây là bước quan trọng nhất. **Lệnh chạy xong không có nghĩa là dữ liệu đã về.**

```bash
docker exec -i aura-prod-frappe-1 bash -lc \
  "cd /home/frappe/frappe-bench && bench --site <site> console" <<'EOF'
print("APP", "auraos" in frappe.get_installed_apps())
print("DEALS", frappe.db.count("Deal"), "JOBS", frappe.db.count("Job"))
EOF
```

**Thành công:** `APP True`, và số deal/job khớp với những gì anh nhớ về ngày sao
lưu. Sau đó mở `https://<domain>/aura-next` bằng trình duyệt và đăng nhập.

**Nếu `APP False`:** database về nhưng app chưa cài. Đây là hỏng thật, không phải
lỗi gõ lệnh. Dừng lại và gọi người dựng hệ thống.

**Nếu số đếm bằng 0 mà lẽ ra phải có dữ liệu:** đừng chạy lại lệnh khôi phục lần
nữa lên site đó. Lấy archive khác (bản cũ hơn) và làm lại từ 4.1.

---

## 6. Sau khi khôi phục

1. **Đổi mật khẩu Administrator** nếu nghi ngờ máy chủ cũ bị xâm nhập.
2. **Chạy một lần sao lưu ngay**, để bản đầu tiên của máy mới nằm trên NAS:
   ```bash
   AURA_BACKUP_PROJECT=aura-prod AURA_BACKUP_SITE=<site> scripts/backup.sh
   ```
3. **Kiểm tra dấu vết sao lưu** (có từ #152):
   ```bash
   scripts/backup-check.sh
   ```
   **Thành công:** báo bản sao lưu gần nhất và tuổi của nó. Nếu nó báo không có
   dấu vết nào, cron chưa chạy trên máy mới: kiểm tra `crontab -l`.
4. **Bật lại cron sao lưu đêm** trên máy mới. Máy mới không có crontab của máy cũ.

---

## 7. Những thứ KHÔNG nằm trong bản sao lưu

Ghi ra đây để không ai đi tìm chúng trong lúc gấp:

- `docker/.env.prod` (mật khẩu) - xem bước 1
- Cấu hình reverse proxy và chứng chỉ TLS - thuộc về proxy, không thuộc app
- Crontab của máy chủ - phải tạo lại
- Bản thân mã nguồn - lấy từ git, xem bước 3

---

## 8. Diễn tập

Bản sao lưu chưa từng khôi phục thử là bản sao lưu không tồn tại
(docs/02 §Backup).

- `scripts/restore-test.sh` chạy mỗi quý, tự khôi phục vào một site tạm rồi xoá.
  Nó chứng minh **archive dùng được**, không chứng minh **anh làm được**.
- Tài liệu này chứng minh vế thứ hai, và chỉ khi có người đi qua nó một lần.
  **Hãy diễn tập một lần trên máy không phải production**, bấm giờ, rồi điền vào
  bước 0.
