# Tingbox cho Home Assistant

Custom integration **không chính thức** cho loa Tingbox, được xây dựng từ luồng
REST/MQTT của ứng dụng Tingbox. Integration này dành cho phần cloud đã xác minh;
nó không thay thế ứng dụng chính thức trong bước cấp Wi-Fi/BLE ban đầu.

> **Phiên bản:** `0.2.0` · **Ngày kiểm thử:** `15/08/2026` · **Home Assistant
> lab:** `2026.2.3`

## Vì sao là custom integration, không phải add-on?

Chọn **custom integration** vì toàn bộ phần cloud cần thiết chạy trực tiếp trong
Home Assistant bằng `aiohttp` và `paho-mqtt`: config flow, REST polling, MQTT
push, entity và re-auth đều thuộc lifecycle của một integration. Add-on chỉ đáng
làm khi cần một daemon/bridge riêng, ví dụ cầu nối BLE/SoftAP hoặc proxy MQTT
cục bộ; APK hiện tại chưa cung cấp giao thức local đủ ổn định cho lớp đó.

Kết luận này có nghĩa là “full tính năng cloud an toàn đã giải được”, không phải
cam kết sao chép 100% mọi màn hình của app. Các bước provisioning Wi-Fi/4G,
chuyển nhượng loa, KYC/ngân hàng và QR vẫn dùng app chính thức.

## Tính năng

- Đăng nhập bằng config flow; tự sinh và lưu một `device_token` riêng cho Home
  Assistant; tự re-login khi token cloud hết hạn.
- REST: danh sách loa được gán, mã trạng thái, khả năng độ sáng, tổng tiền hiện
  tại, số giao dịch và chế độ Tingbox.
- MQTT v5/TLS: theo dõi kết nối cloud, nhận giao dịch và chỉ giữ số tiền, loại
  broadcast cùng fingerprint của `request_id` để chống lặp.
- Event bus `tingbox_payment` và event entity `Nhận giao dịch`, chỉ phát amount
  và currency `VND`, không phát QR/tài khoản/tên người trả.
- Điều khiển độ sáng màn hình mức `1..7` cho thiết bị trả `isBrightness=true`.
  Cloud dùng mức ngược `backlight_level = 7 - mức_HA`.
- Công tắc **Âm báo giao dịch trên ứng dụng** ánh xạ trường
  `type_receiver_tingting` mà màn hình “Tuỳ chọn âm thanh” sử dụng. Đây là âm
  báo trên điện thoại chạy app, không phải volume phần cứng của loa.
- Hiện QR mặc định dưới dạng boolean an toàn, số loa, số loa hỗ trợ độ sáng,
  lần cập nhật cloud gần nhất, loại loa, kênh thiết bị và mô tả trạng thái.
- Nút **Làm mới dữ liệu cloud** để gọi REST refresh ngay thay vì chờ chu kỳ.
- Diagnostics được rút gọn; không xuất token, mật khẩu MQTT, topic, client ID,
  serial, QR, bank, số tài khoản hoặc dữ liệu KYC.

## Chưa hỗ trợ

- Không có điều khiển âm lượng phần cứng đã được xác minh. Nút “Nghe thử” của
  app phát bộ âm thanh cục bộ trên điện thoại, không phải lệnh test loa cloud.
- Không tự provision Wi-Fi/BLE/SoftAP; Android app cần quyền Nearby/Bluetooth
  và thao tác vật lý trên loa.
- Không thực hiện transfer/assign, đổi QR, liên kết ngân hàng, KYC hoặc giao dịch.
- Chưa tuyên bố live end-to-end cho event thanh toán và lệnh ghi độ sáng; các
  bước này cần loa online và một giao dịch/lệnh thử do người dùng chủ động cho
  phép.

## Cài đặt qua HACS

1. Đẩy repository này lên GitHub, giữ nguyên thư mục
   `custom_components/tingbox/` ở root.
2. Trong HACS mở **Custom repositories**, nhập URL repository, chọn loại
   **Integration**.
3. Cài **Tingbox**, khởi động lại Home Assistant.
4. Vào **Settings → Devices & services → Add integration → Tingbox** và nhập
   tài khoản Tingbox.vn.
5. Nếu flow báo chứng chỉ MQTT cũ, chỉ chọn **Cho phép MQTT TLS không xác minh
   chứng chỉ** khi bạn hiểu rủi ro và tin cậy mạng. Tùy chọn này có thể đổi lại
   trong Options.

HACS metadata nằm trong `hacs.json`; brand icon nằm trong
`custom_components/tingbox/brand/icon.png`. Nếu tên GitHub khác
`trankhanhduy2912/tingbox-hass`, sửa các trường `documentation` và
`issue_tracker` trong `manifest.json` trước khi publish.

## Cài thủ công

Giải nén gói phát hành rồi chép thư mục
`custom_components/tingbox` vào `/config/custom_components/tingbox`. Đường dẫn
cuối cùng phải có:

```text
/config/custom_components/tingbox/manifest.json
```

Khởi động lại Home Assistant và thêm integration như ở bước 4 bên trên.

## Entity và automation

Integration tạo một thiết bị cloud `Tingbox Cloud`, một thiết bị cho mỗi loa
được gán, cùng các entity sau:

| Entity | Ý nghĩa |
| --- | --- |
| `Kết nối MQTT` | Kết nối tới broker cloud, không phải trạng thái nguồn vật lý |
| `Tổng tiền hiện tại` | Aggregate do API cấu hình tài khoản trả về |
| `Số giao dịch` | Aggregate do API cấu hình tài khoản trả về |
| `Chế độ hiện tại` | Mode cloud hiện tại |
| `Giao dịch gần nhất` | Amount cuối cùng nhận qua MQTT |
| `Thời điểm giao dịch gần nhất` | Timestamp event cuối |
| `Nhận giao dịch` | Event entity với event type `payment` |
| `Trạng thái loa` | `status_code` của loa được gán |
| `Độ sáng màn hình` | Slider `1..7`, chỉ có trên loa hỗ trợ |
| `Âm báo giao dịch trên ứng dụng` | Bật/tắt âm báo ở app Tingbox trên điện thoại |
| `QR mặc định đã cấu hình` | Chỉ trả có/không, không đưa nội dung QR vào HA |
| `Số loa được gán` | Số thiết bị hiện thuộc tài khoản |
| `Số loa hỗ trợ độ sáng` | Số thiết bị có cờ `isBrightness=true` |
| `Cập nhật cloud gần nhất` | Lần REST refresh thành công gần nhất |
| `Mô tả trạng thái` | Chuỗi trạng thái do API trả về |
| `Loại loa` | Category/model thiết bị từ app cloud |
| `Kênh thiết bị` | `channelDescription` nếu API có trả |
| `Hỗ trợ điều chỉnh độ sáng` | Capability dạng binary sensor theo loa |
| `Làm mới dữ liệu cloud` | Nút ép coordinator cập nhật ngay |

Ví dụ automation dùng event bus:

```yaml
automation:
  - alias: "Thông báo khi Tingbox nhận tiền"
    triggers:
      - trigger: event
        event_type: tingbox_payment
    actions:
      - action: notify.mobile_app_dien_thoai
        data:
          message: "Tingbox nhận {{ trigger.event.data.amount }} VND"
```

Đặt độ sáng bằng action chuẩn của Home Assistant:

```yaml
action: number.set_value
target:
  entity_id: number.tingbox_do_sang_man_hinh
data:
  value: 5
```

Bật âm báo giao dịch trên ứng dụng điện thoại:

```yaml
action: switch.turn_on
target:
  entity_id: switch.tingbox_am_bao_giao_dich_tren_ung_dung
```

Nếu cloud chưa từng trả `type_receiver_tingting`, công tắc vẫn được tạo nhưng ở
trạng thái unavailable; integration không tự đoán giá trị để tránh ghi sai cấu
hình tài khoản. Sau khi đã có một giá trị hợp lệ, lần refresh tạm thời thiếu
field sẽ giữ trạng thái gần nhất thay vì làm entity chập chờn.

## TLS MQTT legacy

Trong lần kiểm tra ngày **14/08/2026**, leaf certificate của broker động từ API
có ngày hết hạn **12/04/2025**. Ứng dụng APK cài callback
`onBadCertificate` trả về chấp nhận, vì vậy integration có một opt-in riêng để
tương thích. Chế độ mặc định vẫn xác minh CA chuẩn; nếu nhà cung cấp gia hạn
certificate, hãy tắt tùy chọn insecure.

Không dùng `allow_insecure_mqtt` trên mạng không tin cậy. Đây là giới hạn của
dịch vụ hiện tại, không phải khuyến nghị bảo mật chung.

## Kiểm thử và phát hành

Chạy từ root repository:

```bash
PYTHONPATH=/opt/apk-lab/projects/tingbox_hass:/opt/apk-lab/ha-test \
  python3 -m unittest discover -s tests -v
python3 scripts/validate_release.py
python3 scripts/build_release.py /duong-dan/ket_qua
```

`build_release.py` tạo ZIP timestamp cố định và file SHA-256. Gói không chứa APK
gốc, dump JADX/Apktool, payload giao dịch, credential, token, QR hay file tạm.

## Phạm vi reverse engineering

Bằng chứng chi tiết nằm trong `REPORT.md`. Các file PoC ở `poc/` là offline và
chỉ in dữ liệu đã rút gọn. Không đưa payload thật vào issue hoặc pull request.

Tham chiếu quy trình integration: [Home Assistant integration file
structure](https://developers.home-assistant.io/docs/creating_integration_file_structure/),
[config entries](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)
và [HACS publish integration](https://www.hacs.xyz/docs/publish/integration/).
