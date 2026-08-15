# Changelog

## 0.2.0 - 2026-08-15

- Thêm công tắc cloud cho âm báo giao dịch trên ứng dụng Tingbox; entity chỉ
  khả dụng khi API trả trạng thái `type_receiver_tingting`.
- Thêm trạng thái QR mặc định dạng boolean, số loa, số loa hỗ trợ độ sáng và
  thời điểm cập nhật cloud gần nhất.
- Thêm entity chẩn đoán theo loa cho mô tả trạng thái, loại loa, kênh thiết bị
  và khả năng điều chỉnh độ sáng.
- Thêm nút làm mới dữ liệu cloud và giữ nguyên redaction cho QR, serial, MQTT,
  ngân hàng và dữ liệu định danh.
- Chuẩn hóa chuỗi boolean như `"false"` khi rút gọn trạng thái QR và giữ giá trị
  âm báo hợp lệ gần nhất nếu một lần refresh tạm thời thiếu field cloud.
- Viết lại README đầy đủ với nút cài HACS và đồng bộ metadata sang repository
  `trankhanhduy2929-beep/tingbox-cloud-home-assistant`.

## 0.1.0 - 2026-08-14

- Thêm config flow tài khoản/mật khẩu và reauthentication.
- Thêm REST polling cho danh sách loa, trạng thái, tổng tiền, số giao dịch và
  chế độ cloud.
- Thêm MQTT v5/TLS cho sự kiện giao dịch đã rút gọn dữ liệu.
- Thêm điều khiển độ sáng màn hình mức `1..7` cho thiết bị hỗ trợ.
- Thêm diagnostics với redaction nghiêm ngặt và tùy chọn TLS MQTT cũ có xác
  nhận rõ ràng.
