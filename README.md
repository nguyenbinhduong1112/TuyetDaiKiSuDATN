<div align="center">
  <img src="https://img.icons8.com/color/96/000000/delivery-scooter.png" alt="Logo"/>
  <h1>VinhUmbrella Logistics ☂️</h1>
  <p><strong>Hệ thống quản lý vận tải và giao nhận thông minh (Logistics Management System)</strong></p>
  
  [![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org)
  [![Streamlit](https://img.shields.io/badge/Streamlit-Framework-FF4B4B.svg)](https://streamlit.io)
  [![Security](https://img.shields.io/badge/Security-JWT_Auth-brightgreen.svg)]()
</div>

---

## 🌟 Giới thiệu (Introduction)
**VinhUmbrella Logistics** là hệ thống quản lý giao nhận và kho bãi trực quan, được xây dựng trên nền tảng **Streamlit**. Hệ thống cung cấp giải pháp toàn diện cho 3 nhóm người dùng chính, giúp tối ưu hóa quy trình vận chuyển từ lúc nhận đơn đến khi giao hàng thành công.

## ✨ Tính năng nổi bật (Features)

### 👮 Về phía Quản trị viên (Admin)
- Quản lý tổng quan hệ thống, tài xế và khách hàng.
- Theo dõi đơn hàng theo thời gian thực (Real-time Tracking).
- Phân bổ đơn hàng cho tài xế một cách tối ưu.
- Thống kê doanh thu và báo cáo hiệu suất giao hàng.

### 🛵 Về phía Tài xế vận hành (Driver)
- Nhận đơn hàng được phân công nhanh chóng.
- Cập nhật trạng thái giao hàng (Đang giao, Thành công, Thất bại).
- Xem lịch sử các chuyến hàng đã hoàn thành và doanh thu cá nhân.

### 👥 Về phía Khách hàng (Customer)
- Đặt đơn vận chuyển mới dễ dàng.
- Theo dõi lộ trình và trạng thái đơn hàng của mình.
- Quản lý lịch sử giao dịch và đánh giá chất lượng dịch vụ.

---

## 🚀 Hướng dẫn cài đặt & Chạy dự án (Installation & Run)

### Yêu cầu hệ thống (Prerequisites)
- Python 3.9 trở lên
- Git

### Các bước cài đặt
**1. Clone dự án về máy**
```bash
git clone https://github.com/nguyenbinhduong1112/TuyetDaiKiSuDATN.git
cd TuyetDaiKiSuDATN
```

**2. Tạo và kích hoạt môi trường ảo (Virtual Environment)**
```bash
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt (Windows)
venv\Scripts\activate

# Kích hoạt (Mac/Linux)
source venv/bin/activate
```

**3. Cài đặt các thư viện phụ thuộc**
```bash
pip install -r requirements.txt
```

**4. Khởi chạy ứng dụng**
```bash
streamlit run main.py
```

Ứng dụng sẽ tự động mở trên trình duyệt tại địa chỉ: `http://localhost:8501`

---

## 🛠 Công nghệ sử dụng (Tech Stack)
* **Frontend/Backend:** Python & Streamlit
* **Database:** LogisticsDB
* **Authentication:** JSON Web Tokens (JWT)

---

## 🔒 Bảo mật (Security)
* Dự án tích hợp **JWT** để quản lý phiên đăng nhập an toàn, chống việc thay đổi trạng thái trái phép và bảo vệ thông tin người dùng.
* Cơ chế tự động làm sạch URL (URL Cleanup) để tránh lộ thông tin token ra bên ngoài.

---
<div align="center">
  <i>Được phát triển với ❤️ cho Đồ án tốt nghiệp</i>
</div>
