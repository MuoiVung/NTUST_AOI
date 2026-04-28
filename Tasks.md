# 📋 Weekly Tasks — AOI Project
> **Tuần:** 28/04 – 02/05/2026  

---

## 🗓 Timeline Tổng Quan

| Task | Deadline | Status |
|---|---|---|
| [Task 1](#task-1-setup-demo-cloud--script-upload-ảnh) | | |
| [Task 2](#task-2-trang-cấu-hình-thời-gian-lưu-ảnh) | | |
| [Task 3](#task-3-define--clean-up-database-schema) | | |
| [Task 4](#task-4-cập-nhật-chương-trình-cho-2-camera) | | |
| [Task 5](#task-5-phân-tích-giải-pháp-scanner-) | | |
| [Task 6](#task-6-thống-nhất-giao-thức-điều-khiển-grid-với-plc) | | |

---

## Task 1 — Setup Demo Cloud & Script Upload Ảnh
**Mô tả:**
- Setup 1 máy cloud (VM/instance) để làm môi trường demo.
- Viết script tự động upload ảnh (ảnh chất lượng cao + ảnh nén) lên cloud.
- Thiết kế **chu kỳ gửi**: cấu hình được khoảng thời gian giữa mỗi lần gửi (ví dụ: mỗi 5 phút, 10 phút…).

**Deliverables:**
- [ ] Cloud instance đang chạy, có thể truy cập được.
- [ ] Script upload ảnh hoạt động (có tham số cấu hình chu kỳ gửi).
- [ ] Tài liệu tóm tắt cách chạy script.

---

## Task 2 — Trang Cấu Hình Thời Gian Lưu Ảnh
**Mô tả:**
- Thiết lập 1 trang UI để cấu hình:
  - ⏱ Thời gian lưu **ảnh chất lượng cao**
  - ⏱ Thời gian lưu **ảnh nén** (compressed image)
- Các giá trị này phải được lưu vào DB và áp dụng cho quá trình xử lý.

**Deliverables:**
- [ ] Trang cấu hình hiển thị và lưu được setting.
- [ ] Giá trị được đọc và áp dụng vào logic lưu ảnh.

---

## Task 3 — Define & Clean Up Database Schema
**Mô tả:**
- Rà soát toàn bộ các field đang dùng trong DB.
- Định nghĩa rõ ý nghĩa, kiểu dữ liệu, và trạng thái sử dụng của từng field.
- Xoá bỏ hoặc đánh dấu `deprecated` các field không còn dùng.

**Deliverables:**
- [ ] Bảng mô tả schema (field name, type, description, status).
- [ ] DB đã được clean up (migration/script nếu cần).

---

## Task 4 — Cập Nhật Chương Trình Cho 2 Camera
**Mô tả:**
- Cập nhật logic xử lý để hỗ trợ đồng thời **2 camera**.
- Đảm bảo luồng dữ liệu, lưu ảnh và kết quả đều hoạt động đúng với cả 2 camera.

**Deliverables:**
- [ ] Chương trình chạy ổn định với 2 camera.
- [ ] Log/kết quả phân biệt rõ từng camera.

---

## Task 5 — Phân Tích Giải Pháp Scanner 🔍

**Bối cảnh:**
Cần quyết định cách lấy thông tin `Order Number` + `Board Number` khi board đi vào trạm AOI.

#### Giải pháp A — Scanner của họ (họ tự scan)
> Người dùng/operator tại trạm trước đã scan board. Khi board đến AOI, hệ thống nhận `order_number` + `board_number` từ shop floor.

| ✅ Ưu điểm | ❌ Nhược điểm |
|---|---|
| Không cần thêm thiết bị | Phụ thuộc hoàn toàn vào hệ thống của họ |
| Quy trình tự nhiên, không thay đổi thói quen | Nếu họ scan sai hoặc thiếu → AOI không có dữ liệu |
| Dữ liệu đến từ nguồn chính thức | Cần tích hợp API/giao tiếp với shop floor system |

---

#### Giải pháp B — Mình tự scan (vị trí cố định)
> Đặt scanner cố định tại trạm AOI. Board vào → tự động scan barcode → lấy order_number + board_number.

| ✅ Ưu điểm | ❌ Nhược điểm |
|---|---|
| Chủ động, không phụ thuộc hệ thống ngoài | Cần xác định **vị trí dán barcode** cố định trên board |
| Kiểm soát được thời điểm scan | Cần scanner phần cứng + cố định vị trí đặt |
| Dễ validate ngay tại chỗ | Nếu board không có barcode → fail |

---

#### Giải pháp C — OCR 🆕
> Dùng camera AOI hoặc camera riêng để **đọc chữ/số trực tiếp** trên board bằng OCR, không cần barcode.

| ✅ Ưu điểm | ❌ Nhược điểm |
|---|---|
| Không cần barcode/QR code dán thêm | Độ chính xác phụ thuộc vào chất lượng ảnh & font chữ |
| Linh hoạt hơn, dùng lại camera sẵn có | Cần train/cấu hình OCR engine (Tesseract, EasyOCR…) |
| Không phụ thuộc vào thiết bị scan ngoài | Có thể bị ảnh hưởng bởi ánh sáng, góc chụp |

---

**Deliverables Task 5:**
- [ ] Tài liệu phân tích ưu/nhược điểm 3 giải pháp.
- [ ] Đề xuất giải pháp cuối cùng sau khi thảo luận với team.
- [ ] Nếu chọn B hoặc C: xác định vị trí đặt scanner/camera và vị trí dán barcode.

---

## Task 6 — Thống nhất giao thức điều khiển Grid với PLC
**Mô tả:**
- Làm việc với team PLC để xác nhận phương án điều khiển tọa độ quét (Grid).
- Đề xuất phương án **Data-driven**: IPC gửi trực tiếp `grid_rows` và `grid_cols` từ Database xuống thanh ghi PLC.
- Mục tiêu: Tránh việc phải cấu hình Grid cứng trong HMI/PLC cho từng loại mạch.

**Deliverables:**
- [ ] Giao thức truyền nhận (Protocol) giữa IPC và PLC được thống nhất.
- [ ] Xác nhận từ team PLC về khả năng xử lý Grid động.

---

> 💬 **Sync-up:** Hàng ngày cuối ngày báo cáo nhanh tiến độ. Nếu bị block → báo ngay để adjust.
