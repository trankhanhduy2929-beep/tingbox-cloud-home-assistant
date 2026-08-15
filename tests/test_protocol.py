"""Protocol tests that run with the Python standard library."""

from __future__ import annotations

import json
import unittest

from custom_components.tingbox.api import (
    _find_first_key,
    _find_key,
    _parse_configured_state,
    _parse_optional_boolean,
    _parse_optional_integer,
)
from custom_components.tingbox.mqtt import parse_payment_payload


class TingboxProtocolTests(unittest.TestCase):
    """Verify redaction and protocol conversions."""

    def test_payment_parser_keeps_only_safe_fields(self) -> None:
        payload = json.dumps(
            {
                "request_id": "private-request-id",
                "broadcast_type": "1",
                "money": "1.234.000",
                "mobile_user": "private-user",
                "account_number": "private-account",
                "account_name": "private-name",
                "homeqrcode": "private-qr",
            }
        ).encode()
        payment = parse_payment_payload(payload)
        self.assertIsNotNone(payment)
        assert payment is not None
        self.assertEqual(payment.amount, 1_234_000)
        self.assertEqual(payment.broadcast_type, "1")
        self.assertEqual(len(payment.request_fingerprint or ""), 64)
        self.assertNotIn("private", repr(payment))

    def test_qr_only_payload_is_discarded(self) -> None:
        payload = json.dumps(
            {
                "broadcast_type": "4",
                "account_number": "private-account",
                "homeqrcode": "private-qr",
            }
        ).encode()
        self.assertIsNone(parse_payment_payload(payload))

    def test_invalid_payment_values_are_discarded(self) -> None:
        self.assertIsNone(parse_payment_payload(b'{"money": true}'))
        self.assertIsNone(parse_payment_payload(b'{"money": -1}'))
        self.assertIsNone(parse_payment_payload(b'{"money": "-1"}'))
        self.assertIsNone(parse_payment_payload(b'{"money": "1111111111111111111"}'))
        self.assertIsNone(parse_payment_payload(b"not-json"))

    def test_brightness_response_lookup_is_recursive(self) -> None:
        response = {"data": {"result": {"brightLevel": "3"}}}
        raw_level = _parse_optional_integer(_find_key(response, "brightLevel"))
        self.assertEqual(raw_level, 3)
        self.assertEqual(7 - raw_level, 4)

    def test_integer_parser_handles_formatted_vnd(self) -> None:
        self.assertEqual(_parse_optional_integer("12.345.000"), 12_345_000)
        self.assertIsNone(_parse_optional_integer(None))
        self.assertIsNone(_parse_optional_integer(True))

    def test_boolean_parser_handles_cloud_encodings(self) -> None:
        self.assertTrue(_parse_optional_boolean(True))
        self.assertTrue(_parse_optional_boolean(1))
        self.assertTrue(_parse_optional_boolean("ON"))
        self.assertFalse(_parse_optional_boolean(False))
        self.assertFalse(_parse_optional_boolean(0))
        self.assertFalse(_parse_optional_boolean("false"))
        self.assertIsNone(_parse_optional_boolean("unknown"))

    def test_qr_configuration_state_never_exposes_raw_value(self) -> None:
        self.assertFalse(_parse_configured_state(None))
        self.assertFalse(_parse_configured_state("false"))
        self.assertFalse(_parse_configured_state(""))
        self.assertTrue(_parse_configured_state("private-qr-payload"))
        self.assertTrue(_parse_configured_state({"private": "qr"}))

    def test_phone_announcement_lookup_supports_both_key_styles(self) -> None:
        snake_case = {"data": {"type_receiver_tingting": True}}
        camel_case = {"result": {"typeReceiverTingTing": "0"}}
        self.assertTrue(
            _parse_optional_boolean(
                _find_first_key(
                    snake_case,
                    ("type_receiver_tingting", "typeReceiverTingTing"),
                )
            )
        )
        self.assertFalse(
            _parse_optional_boolean(
                _find_first_key(
                    camel_case,
                    ("type_receiver_tingting", "typeReceiverTingTing"),
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
