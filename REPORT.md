# Báo cáo phân tích Tingbox và thiết kế Home Assistant

**Ngày lập:** 14/08/2026 · **Cập nhật integration:** 21/08/2026  
**Phạm vi:** APK Tingbox do người dùng cung cấp và các endpoint cloud mà tài
khoản được phép truy cập.  
**Kết luận kiến trúc:** custom integration; không cần add-on ở phiên bản này.

## 1. Tóm tắt

APK là `vn.nextpay.mpos360`, bản hiển thị `2.5.5` (code `128`), Flutter/Shorebird.
Phần cloud đã giải được dùng REST trên hai host NextPay và MQTT v5/TLS. REST +
MQTT có thể chạy trực tiếp trong process Home Assistant, vì vậy add-on không
đem lại lợi ích tương xứng và sẽ tạo thêm một daemon/container cùng bề mặt
credential.

Phân tích AOT phục hồi được thực hiện trên artefact ARM64 tương ứng bản `2.5.2`
do Shorebird split; các endpoint quan trọng đã được đối chiếu với APK hiện tại
và gọi smoke test bằng phiên được cấp quyền. Vì vậy các phần có dấu “đã xác
minh” bên dưới là protocol-level, còn khác biệt UI giữa `2.5.2` và `2.5.5` vẫn
được ghi là giới hạn.

## 2. Đã xác minh

### REST/auth

- App-core: `https://tingbox-appcore.nextpay.vn/`.
- Đăng nhập: `POST api/auth/login`, body tối thiểu gồm `value`, `password`,
  `deviceToken`, `os`; token trả về được gửi ở header `Authorization` không có
  tiền tố `Bearer`.
- Danh sách thiết bị: `POST api/transfer-device/list-device`, body `{}`.
- Kiểm tra liên kết: `POST api/check-connect-device`, body có `serial`.
- Lấy cấu hình merchant/cloud: `POST Mpos360GetCauHinhByMerchant` với
  `merchantId`, `username`, `os=ANDROID`, `deviceToken`, `versionChange=2`.
- Cấu hình trả `clientId`, MQTT broker, username/password MQTT, topic riêng,
  aggregate total/count và mode. QR, bank, mobile-user và KYC bị loại khỏi
  integration.

### MQTT

- App dùng package `mqtt5_client`, client MQTT v5 và TLS.
- Port được giải mã từ tagged Smi trong `MqttManager.initialize` là `8883`.
- Broker, credential, client ID và topic đều lấy động từ REST; không hardcode
  vào repository.
- Topic riêng có bốn segment và được subscribe với QoS 1.
- Smoke probe ngày 14/08/2026: TLS socket tới broker thành công khi dùng hành
  vi tương thích app; CONNACK reason `0`; SUBACK reason `1`; không nhận payload
  giao dịch trong khoảng chờ. Không lưu payload thô.
- Handler app phân nhánh `broadcast_type` và đọc `money` cho payment. Handler QR
  đọc các khóa `mobile_user`, `device_id`, `homeqrcode`, `qr_type`, `qr_id`,
  `account_number`, `account_name`, `payment_amount`; integration cố ý bỏ toàn bộ
  nhánh QR.

### Độ sáng

- Thiết bị trả cờ `isBrightness=true` được app hiển thị control.
- Đọc: `POST api/mc-device/get-info-config` với `{mcId, clientId}`; app tìm
  trường `brightLevel`.
- Ghi: `POST api/mc-device/publish-message-config` với `{mcId, clientId,
  backlight_level}`.
- UI app dùng mức 1–7 và đổi sang wire bằng `7 - slider`; integration giữ cùng
  quy ước để người dùng không phải biết giá trị raw 0–6.
- Smoke test REST hiện tại trả ACK thành công nhưng không có `brightLevel`, nên
  integration giữ state `unknown` cho tới khi loa trả cấu hình. Không gửi lệnh
  ghi trong quá trình reverse engineering.

### Âm báo ứng dụng và metadata an toàn

- APK gọi `Mpos360DeviceGetTypeReceiverTingTing` để đọc và
  `Mpos360DeviceUpdateTypeReceiverTingTing` để cập nhật boolean
  `type_receiver_tingting`.
- Controller màn hình dùng một `RxBool`; nút “Nghe thử” gọi bộ ghép audio cục bộ
  của ứng dụng điện thoại. Đây không phải endpoint volume/test loa phần cứng.
- Integration tạo switch account-level nhưng chỉ cho thao tác sau khi API từng
  trả trạng thái. Nếu endpoint chưa từng trả field, entity ở unavailable thay
  vì đoán mặc định; lần refresh thiếu field sau đó giữ giá trị hợp lệ gần nhất.
- `qrDefault` chỉ được rút thành boolean có/không; `channelDescription`, category
  và status được đưa thành metadata/entity. Nội dung QR, serial đầy đủ,
  `mobileUserId` và `otherData` không được lưu.

### TLS certificate

- Leaf certificate quan sát được có SAN `*.nextpay.vn`, issuer GlobalSign và hết
  hạn ngày 12/04/2025; ngày kiểm tra là 14/08/2026.
- AOT có callback `MqttManager._onBadCertificate`; thân hàm giải mã trả object
  boolean chấp nhận. Đây là lý do app vẫn có thể kết nối khi CA chuẩn từ chối.
- Integration mặc định strict TLS; config flow chỉ cho phép legacy TLS sau một
  bước xác nhận rõ ràng. Đây là compatibility escape hatch, không phải mặc định
  bảo mật.

### Provisioning/local

- Manifest yêu cầu Internet, Bluetooth/Nearby Wi-Fi và quyền Wi-Fi. AOT có các
  controller `TingboxWifiSpeakerListController`, `TingboxProHelper` và plugin
  Wi-Fi/BLE để tìm/provision loa.
- Chưa có local HTTP/TCP/UDP protocol đủ rõ để thay app; provisioning tiếp tục
  dùng app chính thức. Không tạo add-on bridge giả định.

## 3. Giả thuyết hoặc chưa xác minh

- `get-info-config` chỉ trả `brightLevel` khi loa online/đúng trạng thái màn hình
  QR; phiên smoke test không nhận response MQTT và HTTP chỉ ACK.
- Lệnh ghi độ sáng có thể được cloud chuyển tiếp khi loa online, nhưng chưa chạy
  trên thiết bị thật để tránh thay đổi state ngoài ý muốn.
- Chưa bắt được một payment live, nên event entity/bus event đã được kiểm thử
  bằng payload tổng hợp offline, chưa tuyên bố âm báo hay giao dịch end-to-end.
- Không tìm thấy protocol volume phần cứng đã xác minh. Route
  `AdjustSpeakerVolume` dẫn đến màn hình “Tuỳ chọn âm thanh”; các hàm lân cận
  đổi `type_receiver_tingting` và phát audio demo trên điện thoại, không cung
  cấp range volume device độc lập.
- Hai endpoint âm báo và body boolean được xác minh bằng static APK; chưa gửi
  lệnh thay đổi thật trong reverse-engineering. Integration chỉ gọi lệnh khi
  người dùng chủ động bật/tắt switch trong Home Assistant.
- Firmware có thể thêm broadcast type/field mới; parser chỉ nhận payment khi có
  `money`, bỏ phần còn lại an toàn.

## 4. Artefact bằng chứng

Các đường dẫn dưới đây là evidence đã được làm sạch, không phải dữ liệu phát hành:

- APK manifest: `/opt/apk-lab/analysis/tingbox_run_20260814/apktool/base/AndroidManifest.xml`.
- Endpoint probe schema: `/opt/apk-lab/analysis/tingbox_run_20260814/evidence/login_endpoint_probe.txt`.
- MQTT init/connect/subscribe:
  `analysis/tingbox_run_20260814/unflutter252/asm/MqttManager/initialize_264dbc.txt`,
  `connect_25ef74.txt`, `subscribe_25070c.txt`.
- MQTT dispatch/payment/QR:
  `analysis/tingbox_run_20260814/unflutter252/asm/HomeController/sub_2656e8.txt`,
  `_handleMqttDataPayment@1794116085_266dd8.txt`,
  `_handleMqttDataQR@1794116085_265a0c.txt`.
- Brightness read/write:
  `analysis/tingbox_run_20260814/unflutter252/asm/adjustBrightness_690bcc.txt`,
  `_onSubmitBrightness@2136035704_691654.txt`.
- Sound option:
  `analysis/tingbox_run_20260814/unflutter252/asm/TingBoxSpeakerDetailController/soundOption_6af7d4.txt`,
  `SpeakerSettingController/updateReceiverTingTing_69bd70.txt` và
  `HomeController/updateReceiverTingTing_61d3b4.txt`.
- Wi-Fi/BLE provisioning:
  `analysis/tingbox_run_20260814/unflutter252/asm/TingBoxWifiSpeakerListController/`,
  `TingboxProHelper/` và `WiFiForIoTPlugin/`.

Không đưa raw login response, device token, MQTT config, QR, bank hoặc payload
giao dịch vào repository/ZIP.

## 5. Kiểm thử đã chạy

- Python compilation và import toàn bộ module custom integration trên Home
  Assistant `2026.2.3`.
- Unit tests standard library: payment redaction, QR discard, brightness
  mapping, boolean sound setting, integer parsing và metadata.
- REST smoke client: một thiết bị được gán, một thiết bị hỗ trợ brightness, MQTT
  port 8883/topic bốn segment; không in identifier hoặc credential.
- MQTT v5/TLS probe chỉ subscribe private topic, gọi `get-info-config`, không
  publish command và không lưu payload.
- Deterministic ZIP sẽ được kiểm tra lại bằng `scripts/validate_release.py` và
  SHA-256 trước khi bàn giao.

## 6. Chính sách an toàn

- Không sửa APK gốc.
- Không lưu hoặc phát hành credential, token, serial đầy đủ, QR, ngân hàng, KYC,
  mobile-user hay payload giao dịch thô.
- Không gọi transfer/assign, publish audio, test speaker hoặc lệnh ghi độ sáng
  trong reverse-engineering smoke test.
- Diagnostics chỉ trả count/flags/hash định danh; event chỉ trả amount VND.
