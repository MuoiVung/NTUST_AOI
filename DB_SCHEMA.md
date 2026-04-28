# NTUST AOI — Database Schema Documentation

Hệ thống sử dụng **PostgreSQL** làm cơ sở dữ liệu chính để quản lý dữ liệu kiểm tra. Dưới đây là cấu trúc chi tiết của các bảng.

---

## 1. Bảng `runs` (Thông tin lượt chạy kiểm tra)
Quản lý thông tin tổng quan của mỗi lần bo mạch đi qua hệ thống kiểm tra.

| Cột | Kiểu dữ liệu | Mô tả |
| :--- | :--- | :--- |
| `run_code` **(PK)** | `VARCHAR(50)` | Mã định danh duy nhất cho mỗi lượt chạy (ví dụ: RUN_2024...). |
| `machine_id` | `VARCHAR(50)` | ID của máy thực hiện kiểm tra. |
| `board_code` | `VARCHAR(20)` | Mã loại bo mạch hoặc số lô. |
| `date_str` | `CHAR(8)` | Ngày kiểm tra định dạng `YYYYMMDD` (Dùng để filter nhanh). |
| `side` | `VARCHAR(10)` | Mặt bo mạch (Top/Bottom). |
| `illumination` | `VARCHAR(20)` | Cấu hình ánh sáng (ví dụ: "LRTB"). |
| `status` | `VARCHAR(20)` | Trạng thái lượt chạy (`COMPLETED`, `PENDING`). Mặc định: `COMPLETED`. |
| `note` | `TEXT` | Ghi chú tổng quát về lượt chạy. |
| `start_time` | `TIMESTAMP` | Thời điểm bắt đầu thực tế. |
| `created_at` | `TIMESTAMP` | Thời điểm bản ghi được tạo (Hệ thống tự động). |

**Chỉ mục (Indexes):**
*   `idx_runs_date`: Tối ưu hóa việc lọc theo ngày.
*   `idx_runs_board_date`: Tối ưu hóa việc tìm kiếm lượt chạy mới nhất của một loại bo cụ thể.

---

## 2. Bảng `images` (Thông tin ảnh chụp chi tiết)
Lưu trữ thông tin về từng ảnh chụp được trong mỗi lượt chạy.

| Cột | Kiểu dữ liệu | Mô tả |
| :--- | :--- | :--- |
| `image_id` **(PK)** | `UUID` | ID định danh duy nhất (Tự động tạo bằng `uuid-ossp`). |
| `run_code` **(FK)** | `VARCHAR(50)` | Liên kết tới bảng `runs`. |
| `file_path` | `TEXT` | Đường dẫn tuyệt đối đến file ảnh trên ổ đĩa. |
| `row_idx` | `INTEGER` | Vị trí hàng trong lưới quét (Grid). |
| `col_idx` | `INTEGER` | Vị trí cột trong lưới quét (Grid). |
| `condition` | `VARCHAR(10)` | Kết quả kiểm tra ảnh (`PASS`, `FAIL`, `PENDING`). |
| `capture_time` | `TIMESTAMP` | Thời điểm máy ảnh chụp file này. |
| `file_name` | `VARCHAR(255)` | Tên file gốc. |
| `file_size_bytes` | `BIGINT` | Dung lượng file (Dùng để kiểm tra tính toàn vẹn). |
| `checksum` | `VARCHAR(64)` | Mã băm file (Tùy chọn, dùng để tránh trùng lặp). |
| `note` | `TEXT` | Ghi chú riêng cho từng ảnh (ví dụ: mô tả lỗi cụ thể). |

**Ràng buộc (Constraints):**
*   `fk_run`: Khóa ngoại liên kết với `runs(run_code)`. Khi một `run` bị xóa, toàn bộ `images` liên quan sẽ tự động bị xóa (`ON DELETE CASCADE`).

**Chỉ mục (Indexes):**
*   `idx_images_run_code`: Tối ưu hóa việc tải nhanh danh sách ảnh của một lượt chạy.
*   `idx_images_condition`: Hỗ trợ thống kê nhanh số lượng ảnh Pass/Fail.

---

## 3. Thông số kết nối (Docker)
*   **Port nội bộ:** `5432`
*   **Port công khai:** `5433` (Dùng port này khi kết nối từ bên ngoài Docker)
*   **Database Name:** `pcb_aoi_db`
