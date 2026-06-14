# PSD Batch Creator

![Python](https://img.shields.io/badge/Python-3.x-blue)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)
![Version](https://img.shields.io/badge/Version-1.1-orange)

## Giới thiệu

**PSD Batch Creator** là ứng dụng desktop viết bằng **Python** và **PyQt6**, hỗ trợ tạo hàng loạt file Photoshop `.psd` trên **macOS** và **Windows**.

## Chức năng chính

* Tạo hàng loạt file `.psd` với màu nền, kích thước và độ phân giải tùy chỉnh.
* Nhập dữ liệu từ bảng (Excel, Google Sheets, v.v) bằng thao tác paste.
* Nhập dữ liệu nhanh bằng văn bản nhiều dòng.
* Hỗ trợ tạo file trong thư mục con của đường dẫn Output.

## Hướng dẫn sử dụng

### Tab 1: Table Input

Dán dữ liệu từ Excel hoặc Google Sheets với cấu trúc như sau (hãy sao chép cả dòng tiêu đề):
| Sub directory | File name | Background color | Width | Height | Resolution |
|---------------|-----------|:----------------:|:-----:|:-------|:----------:|
|               | Poster    | `#f0f1f2`        | 4200  | 4800   | 300        |
| Animals       | Cat       | `#010203`        | 4200  | 4800   | 300        |
| Animals       | Dog       | `#040506`        | 4200  | 4800   | 300        |

Cột `Sub directory` không bắt buộc nhập.

### Tab 2: Text Input

Tạo file tại thư mục Output:
```text
#f0f1f2 Poster
```

Tạo file trong thư mục con:
```text
Animals #010203 Cat
```

**Lưu ý:** Các file tạo từ tab **Text Input** có kích thước mặc định `4200x4800` với độ phân giải `300ppi`.

Sau khi nhập dữ liệu, chọn thư mục Output và bấm **Create Batch Files**.
