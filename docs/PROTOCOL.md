# Ghi chú protocol

Tài liệu chi tiết nằm ở `REPORT.md`. File này giữ các quy ước mà code sử dụng:

| Thành phần | Quy ước |
| --- | --- |
| Auth | REST token ở header `Authorization`, không thêm `Bearer` |
| MQTT | MQTT v5, TLS, port động mặc định 8883, topic lấy từ cloud |
| Payment | Chỉ nhận payload có `money`; QR payload bị bỏ |
| Brightness | HA `1..7` ↔ wire `backlight_level 6..0` |
| Phone sound | `Mpos360DeviceGetTypeReceiverTingTing` và `Mpos360DeviceUpdateTypeReceiverTingTing`; boolean `type_receiver_tingting` |
| QR state | Chỉ giữ boolean có cấu hình `qrDefault`, không giữ nội dung |
| Privacy | Không lưu raw MQTT/QR/bank/mobile-user |

Mọi field mới cần được kiểm thử bằng payload tổng hợp trước khi thêm vào state.
