"""Constants for the Tingbox integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "tingbox"
NAME = "Tingbox"
VERSION = "0.2.2"

APP_CORE_BASE_URL = "https://tingbox-appcore.nextpay.vn/"
MCMN_BASE_URL = "https://tingbox-mcmn.nextpay.vn/"

CONF_DEVICE_ID = "device_token"
CONF_ALLOW_INSECURE_MQTT = "allow_insecure_mqtt"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL_MINUTES = 5
DEFAULT_SCAN_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)
MIN_SCAN_INTERVAL_MINUTES = 1
MAX_SCAN_INTERVAL_MINUTES = 60

BRIGHTNESS_MIN = 1
BRIGHTNESS_MAX = 7

EVENT_PAYMENT = "tingbox_payment"
