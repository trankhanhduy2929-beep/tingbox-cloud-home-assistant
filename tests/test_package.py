"""Package metadata tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TingboxPackageTests(unittest.TestCase):
    """Validate files required by Home Assistant and HACS."""

    def test_manifest(self) -> None:
        manifest = json.loads(
            (ROOT / "custom_components/tingbox/manifest.json").read_text()
        )
        self.assertEqual(manifest["domain"], "tingbox")
        self.assertEqual(manifest["version"], "0.2.0")
        self.assertTrue(manifest["config_flow"])
        self.assertIn("paho-mqtt==2.1.0", manifest["requirements"])

    def test_hacs_metadata(self) -> None:
        metadata = json.loads((ROOT / "hacs.json").read_text())
        self.assertEqual(metadata["name"], "Tingbox")
        self.assertTrue(metadata["render_readme"])

    def test_extended_entity_platforms(self) -> None:
        component = ROOT / "custom_components/tingbox"
        self.assertTrue((component / "button.py").is_file())
        self.assertTrue((component / "switch.py").is_file())
        strings = json.loads((component / "strings.json").read_text())
        self.assertIn("phone_announcements", strings["entity"]["switch"])
        self.assertIn("refresh_cloud_data", strings["entity"]["button"])
        self.assertIn(
            "qr_default_configured",
            strings["entity"]["binary_sensor"],
        )

    def test_no_compiled_or_sensitive_temp_files(self) -> None:
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            self.assertFalse(path.name.startswith("tingbox_login"))
            self.assertFalse(path.name.startswith("tingbox_config_candidate"))


if __name__ == "__main__":
    unittest.main()
