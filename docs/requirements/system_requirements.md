# System Requirements & Architectural Updates

## 1. Loại bỏ pgAdmin 4 khỏi Docker Compose
- **Mô tả:** Xoá service `pgadmin` khỏi file `docker-compose.yml`.
- **Lý do:** Người dùng đã có sẵn pgAdmin 4 bản Desktop. Việc chạy thêm pgAdmin trong Docker gây lãng phí tài nguyên RAM/CPU của máy tính công nghiệp (IPC) và dư thừa port (5050). Người dùng chỉ cần dùng pgAdmin Desktop kết nối thẳng vào `localhost:5433` (port của PostgreSQL đã được expose).

## 2. Giao tiếp với hệ thống Shopfloor (SerialTest API)
- **Mô tả:** Xây dựng một service (hoặc thêm chức năng vào FastAPI backend) để gọi HTTP GET request tới API của Shopfloor khi có mã vạch (Serial Number) mới được quét.
- **API Endpoint:** `https://tracking.aaeon.com.tw/ashx/WebAPI/Board/SerialTest/HandlerGetSerialInfo.ashx?sn={serial_number}`
- **Lý do:** Dựa theo tài liệu v1.0, hệ thống cần tự động lấy thông tin `PCB_Length` và `PCB_Width`. Từ kích thước thực tế này, kết hợp với trường nhìn (FOV - Field of View) của camera, hệ thống có thể tự động tính toán ra số lượng ảnh cần quét (`grid_rows`, `grid_cols`) mà không cần người dùng nhập tay, tăng tính tự động hóa theo đúng định hướng Data-driven.

## 3. Tích hợp Máy tính AI (AI Inference Node)
- **Mô tả:** Mở rộng schema cơ sở dữ liệu bảng `images`, thêm cột `ai_status` (ví dụ: `PENDING`, `PROCESSING`, `DONE`). 
- **Quy trình chuẩn:** 
  1. Thêm API endpoint `GET /api/images/pending-ai` để máy AI liên tục gọi (Polling) lấy danh sách ảnh cần phân tích.
  2. Máy AI tải ảnh về thông qua endpoint proxy hiện tại `GET /images/proxy/{image_id}`.
  3. Máy AI phân tích và gửi kết quả về qua API `PUT /api/images/{image_id}` (cập nhật cột `condition` thành `PASS`/`FAIL` và các thông tin lỗi).
- **Lý do:** Hệ thống AI thường đòi hỏi cấu hình GPU cao và môi trường Python khác biệt (PyTorch, TensorRT,...). Việc tách bạch máy AI ra (hoặc chạy một process riêng độc lập) giao tiếp qua API sẽ giúp hệ thống chính không bị ảnh hưởng hiệu năng và dễ dàng mở rộng.

## 4. Chốt Kiến Trúc Frontend (Giữ nguyên React + FastAPI)
- **Quyết định:** KHÔNG chuyển sang nền tảng PySide. Giữ nguyên kiến trúc HMI hiện tại (Web UI React + FastAPI Backend).
- **Lý do:** Hệ thống AOI hiện đại không chỉ chạy độc lập mà còn đóng vai trò như một Server cục bộ. Bằng việc dùng FastAPI cung cấp API RESTful, các hệ thống khác trong mạng xưởng (như AI Node lấy ảnh phân tích, hay NAS/Cloud kéo ảnh dự phòng) có thể dễ dàng gọi API HTTP GET trực tiếp từ máy IPC mà không gặp cản trở. Nếu chuyển sang PySide thuần (Desktop Client), khả năng chia sẻ file qua mạng sẽ phải cấu hình thủ công (SMB) hoặc tự viết thêm luồng Web Server rất phức tạp.

## 5. Cập nhật Architecture & State Machine Graphs
- **Mô tả:** Sơ đồ `overall_system_architect.png` là chính xác về mặt kết nối khối. Tuy nhiên cần làm rõ giao thức: 
  - IPC kết nối Shopflow qua `HTTPS GET`.
  - IPC kết nối Cloud (MinIO) qua `S3 API`.
  - PC kết nối với AI thông qua `REST API` mạng nội bộ (hoặc gRPC).
- **Lý do:** Để đảm bảo các thành viên phát triển mới hiểu rõ cách các node nói chuyện với nhau, tránh nhầm lẫn giữa kết nối vật lý (Ethernet/USB) và giao thức phần mềm.
