# PoC giao thức an toàn

`tingbox_protocol.py` là PoC **offline**, không đăng nhập và không gửi lệnh tới
loa. Script chỉ minh họa hai phần đã giải được:

- payload MQTT có trường `money` được rút gọn còn số tiền, loại phát và hash của
  `request_id`; mọi trường QR, ngân hàng, số tài khoản, tên tài khoản và người
  dùng di động bị bỏ;
- độ sáng Home Assistant `1..7` được đổi sang `backlight_level` của cloud
  `6..0`, và ngược lại.

Ví dụ:

```bash
python3 poc/tingbox_protocol.py brightness --ha-level 4
python3 poc/tingbox_protocol.py payment /duong-dan/payload-da-tu-che.json
```

Không dùng payload giao dịch thật khi mở issue công khai.

