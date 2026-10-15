# qgis2ge - QGIS to Google Earth Plugin

[![GitHub Release](https://img.shields.io/badge/release-v1.1.0-blue.svg)](https://github.com/iitold/qgis2ge/releases)
[![QGIS Minimum Version](https://img.shields.io/badge/QGIS-3.22+-brightgreen.svg)](https://qgis.org)
[![License](https://img.shields.io/badge/license-GPLv2%2B-orange.svg)](LICENSE)

*Plugin chuyên dụng cho QGIS (PyQGIS) hỗ trợ xuất các lớp polygon/multipolygon sang Google Earth (`.kmz` / `.kml`) giữ **100% màu sắc fill, viền, độ trong suốt**, phân loại category, bảng thuộc tính và phóng to/thu nhỏ kích thước cánh sóng viễn thông (cell sector).*

---

## 📖 MỤC LỤC / TABLE OF CONTENTS
1. [Hướng dẫn cài đặt lần đầu (First-Time Installation)](#1-hướng-dẫn-cài-đặt-lần-đầu-first-time-installation)
2. [Hướng dẫn cập nhật phiên bản mới (Updating to New Versions)](#2-hướng-dẫn-cập-nhật-phiên-bản-mới-updating-to-new-versions)
3. [Tính năng nổi bật (Key Features)](#3-tính-năng-nổi-bật-key-features)
4. [Cấu trúc mã nguồn (Directory Structure)](#4-cấu-trúc-mã-nguồn-directory-structure)
5. [Tự động hóa phát hành cho Developer (`release.bat`)](#5-tự-động-hóa-phát-hành-cho-developer-releasebat)
6. [Chạy kiểm thử tự động (Unit Tests)](#6-chạy-kiểm-thử-tự-động-unit-tests)

---

## 1. Hướng dẫn cài đặt lần đầu (First-Time Installation)

### 👉 Cách 1: Cài đặt từ file ZIP trong QGIS (Khuyên dùng - Nhanh nhất)
1. **Tải file plugin:** Tải file [qgis2ge.zip](https://github.com/iitold/qgis2ge/releases/latest) từ trang GitHub Releases (hoặc dùng file `qgis2ge.zip` có sẵn trong thư mục repo).
2. **Mở QGIS:** Khởi động QGIS (phiên bản 3.22 LTR trở lên đến 3.40+).
3. **Mở trình quản lý Plugin:** Trên thanh menu trên cùng của QGIS, vào:  
   `Plugins` (Tiện ích) ➔ `Manage and Install Plugins...` (Quản lý và cài đặt tiện ích...).
4. **Chọn cài từ file ZIP:** Ở cột danh mục bên trái, chọn thẻ **Install from ZIP** (Cài đặt từ tệp ZIP).
5. **Chọn file:** Bấm nút browse `...` tại mục *ZIP file* và trỏ tới file `qgis2ge.zip` vừa tải.
6. **Bấm cài đặt:** Nhấn nút **Install Plugin** (Cài đặt tiện ích).  
   *(Khi cài xong, QGIS sẽ hiện thanh thông báo màu xanh: "Plugin installed successfully")*.
7. **Khởi chạy plugin:**
   - Cách 1: Vào menu `Vector` ➔ `qgis2ge` ➔ `qgis2ge: Export to Google Earth...`
   - Cách 2: Bấm vào biểu tượng logo của plugin trên thanh công cụ `Vector Toolbar`.

---

### 👉 Cách 2: Copy thủ công vào thư mục Plugin của QGIS
Nếu bạn muốn cài đặt trực tiếp bằng tay:
1. Bấm tổ hợp phím `Windows + R` để mở hộp thoại Run.
2. Dán đường dẫn sau và bấm `Enter`:
   ```text
   %APPDATA%\QGIS\QGIS3\profiles\default\python\plugins
   ```
3. Copy toàn bộ thư mục [qgis2ge](file:///c:/code/qgis_plugin/qgis-export-kml/qgis2ge) vào thư mục trên.
4. Mở QGIS, vào `Plugins` ➔ `Manage and Install Plugins...` ➔ thẻ `Installed` (Đã cài đặt), tích dấu chọn vào **qgis2ge** để kích hoạt.

---

## 2. Hướng dẫn cập nhật phiên bản mới (Updating to New Versions)

### 🌟 Cách 1: Cập nhật tự động 1-Click ngay trong giao diện Plugin (Khuyên dùng)
Plugin **qgis2ge** được tích hợp sẵn công cụ tự kiểm tra và nâng cấp trực tiếp:
1. Mở plugin **qgis2ge** trong QGIS.
2. Nhìn lên góc trên bên phải của hộp thoại (ngay cạnh huy hiệu phiên bản, ví dụ `v1.1.0`), bấm nút **Check for Updates**.
3. Nếu trên GitHub có bản phát hành mới hơn:
   - Một thanh banner màu xanh sẽ xuất hiện:  
     `★ New version vX.Y.Z available! [Update Now] [Notes]`
4. Bấm nút **Update Now**:
   - Plugin sẽ tự động tải file zip bản mới nhất từ GitHub Releases về máy.
   - Tự giải nén, kiểm tra tính toàn vẹn và cập nhật đè vào thư mục plugin.
   - **Tự động tải lại (hot-reload)** trực tiếp trong phiên làm việc của QGIS mà **không cần khởi động lại QGIS**!
5. **Tự động hóa:** Bạn có thể vào thẻ **Advanced Options** trong hộp thoại và tích chọn `Check for updates automatically when opening dialog` để mỗi lần mở plugin lên, hệ thống sẽ tự động báo nếu có phiên bản mới.

---

### 📦 Cách 2: Cập nhật thủ công bằng file ZIP
Nếu máy tính không có kết nối trực tiếp đến GitHub trong QGIS:
1. Tải file `qgis2ge.zip` bản mới nhất từ [GitHub Releases](https://github.com/iitold/qgis2ge/releases/latest).
2. Vào QGIS ➔ `Plugins` ➔ `Manage and Install Plugins...` ➔ `Install from ZIP`.
3. Trỏ tới file `qgis2ge.zip` mới và bấm **Install Plugin**. QGIS sẽ tự động ghi đè và nâng cấp lên phiên bản mới.

---

## 3. Tính năng nổi bật (Key Features)

- **Giữ nguyên 100% màu sắc và kiểu dáng (Style & Color Fidelity):**
  - Giữ chính xác màu nền (Fill Color), màu viền (Stroke Color), độ dày viền và độ trong suốt (Alpha/Opacity).
  - Hỗ trợ toàn diện mọi kiểu renderer của QGIS: **Single Symbol**, **Categorized (phân loại)**, **Graduated (dải giá trị)**, **Rule-based (theo điều kiện)** và cả **Data-defined override** (màu xác định bằng biểu thức công thức).
- **Hỗ trợ định dạng KMZ và KML:**
  - Xuất ra file `.kmz` (nén zip chuẩn Google Earth chứa `doc.kml`) hoặc `.kml` thuần.
  - KMZ giúp giảm dung lượng file từ **85–90%**, mở trong Google Earth cực kỳ mượt mà, rất thích hợp cho các lớp hàng chục ngàn cell viễn thông.
- **Tùy chỉnh phóng to/thu nhỏ kích thước cánh sóng (Cell Sector Size Scaling):**
  - Cho phép tăng/giảm kích thước cánh sector (ví dụ: +50% = 1.5x) để dễ nhìn hơn trên Google Earth.
  - **Điểm neo Gốc trạm / Vertex đầu tiên (Khuyên dùng cho mạng di động RF/RAN):** Giữ cố định tọa độ chân cột trạm phát sóng, chỉ mở rộng chiều dài búp sóng theo hướng phủ sóng.
  - **Điểm neo Trọng tâm (Centroid):** Phóng to đều xung quanh tâm hình polygon.
- **Tổ chức thư mục Folder theo Category:**
  - Tự động gom các polygon cùng giá trị phân loại vào từng `<Folder>` riêng biệt, dễ dàng bật/tắt từng nhóm trạm/băng tần trên cây thư mục Google Earth Pro.
- **Hiển thị thuộc tính ExtendedData:**
  - Cho phép chọn các cột thuộc tính cần xuất, bấm vào polygon trên Google Earth sẽ hiện bảng thông số chi tiết (Site Name, Cell ID, Azimuth, Height, Downtilt,...).
- **Chạy nền đa luồng (Background QgsTask):**
  - Xử lý mượt mà hàng trăm nghìn polygon bằng cơ chế ghi luồng (streaming) vào file tạm, không tốn RAM, không làm đơ QGIS, có thanh tiến trình và nút Hủy (Cancel).

---

## 4. Cấu trúc mã nguồn (Directory Structure)

```
qgis2ge/
├── __init__.py            # Entrypoint classFactory(iface) cho QGIS Plugin Manager
├── metadata.txt           # Metadata (tên: qgis2ge, version=1.1.0, tác giả: iitold)
├── plugin.py              # Đăng ký Action vào Menu Vector (&qgis2ge) & Toolbar
├── dialog.py              # Giao diện UI tiếng Anh hiện đại, responsive, thẻ card, swatches
├── exporter.py            # Lõi xuất KMZ/KML, thuật toán streaming, deduplication, scaling
├── updater.py             # Bộ máy tự động check update từ GitHub & hot-reload
├── task.py                # Quản lý tác vụ nền bất đồng bộ (QgsTask)
├── styles.qss             # Stylesheet đồng bộ giao diện sáng/tối
├── icon.svg               # Biểu tượng vector plugin
└── tests/
    └── test_exporter.py   # Bộ 14 bài kiểm thử tự động không cần GUI (PyQGIS headless)
```

---

## 5. Tự động hóa phát hành cho Developer (`release.bat`)

Mỗi khi lập trình viên cập nhật tính năng và muốn phát hành phiên bản mới, chỉ cần chạy file script tự động hóa:

### Bước 1: Chạy file `release.bat`
Nhấp đúp chuột vào file [release.bat](file:///c:/code/qgis_plugin/qgis-export-kml/release.bat) hoặc mở terminal:
```cmd
release.bat
```
*(Hoặc truyền tham số: `release.bat 1.2.0 "Bổ sung tính năng mới"`)*

### Quy trình tự động thực hiện:
1. **Thiết lập phiên bản:** Đọc phiên bản hiện tại (ví dụ `1.1.0`), hỏi phiên bản mới (ví dụ `1.2.0`).
2. **Cập nhật tài liệu:** Tự động sửa số version trong `qgis2ge/metadata.txt` và `README.md`.
3. **Chạy kiểm thử an toàn:** Chạy 14 bài test PyQGIS. Nếu có bất kỳ lỗi code nào, script sẽ **dừng lại ngay lập tức** để bảo vệ kho mã nguồn.
4. **Đóng gói file ZIP:** Tự động tạo file sạch `qgis2ge.zip` (loại bỏ `__pycache__` và file test).
5. **Cập nhật máy dev:** Tự copy bản mới vào thư mục QGIS trên máy bạn để kiểm tra ngay.
6. **Cấu hình Git:** Thiết lập Git user `iitold`, remote `https://github.com/iitold/qgis2ge.git`.
7. **Commit & Tag:** Tạo commit và gắn tag `v1.2.0`.
8. **Đẩy lên GitHub:** Xác nhận đẩy nhánh `main` và tag `v1.2.0` lên GitHub.

### Bước 2: GitHub Actions tự động build và phát hành
Khi tag `v1.2.0` được đẩy lên, luồng CI/CD (`.github/workflows/release.yml`) trên GitHub sẽ tự động:
1. Khởi chạy máy ảo Ubuntu.
2. Đóng gói mã nguồn thành `qgis2ge.zip`.
3. Tạo **GitHub Release** chính thức và đính kèm `qgis2ge.zip`.
4. Người dùng mở QGIS bấm **Check for Updates** ➔ **Update Now** là có ngay bản mới!

---

## 6. Chạy kiểm thử tự động (Unit Tests)

Chạy bộ kiểm thử headless độc lập bằng môi trường Python của QGIS:

```cmd
cmd /c call "C:\Program Files\QGIS 3.40.12\bin\python-qgis-ltr.bat" -m unittest qgis2ge.tests.test_exporter
```

Kết quả mong đợi:
```
..............
----------------------------------------------------------------------
Ran 14 tests in 0.951s

OK
```

14 bài test bao quát:
- Chuyển đổi màu hex KML (`aabbggrr`)
- Các chế độ viền (`same`, `same_opaque`, `original`, `none`)
- Gộp style trùng lặp & cấu trúc Folder phân loại
- Polygon có lỗ hổng & MultiPolygon
- Đè màu bằng biểu thức dữ liệu (Data-defined override)
- Xử lý ký tự đặc biệt XML và tiếng Việt có dấu
- Renderer phân dải Graduated & Rule-based phức tạp
- Ghi đè độ trong suốt và độ dày viền
- Bộ lọc chỉ xuất các feature đang chọn
- Xuất nén KMZ và kiểm tra cấu trúc file zip `doc.kml`
- Phóng to cánh sóng viễn thông theo điểm neo gốc trạm
- Kiểm tra logic phiên bản và giải nén của bộ Updater
- Hủy tác vụ an toàn và dọn dẹp file tạm

---

## 7. Giấy phép & Tác giả (License & Author)

- **License:** GNU General Public License v2.0 or later (GPL-2.0-or-later).
- **Tác giả:** **iitold** (`https://github.com/iitold/qgis2ge`).
