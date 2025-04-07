import unittest
from unittest.mock import patch, MagicMock
import bin.ad2_firmwareupload as cli  # update import if needed


class TestFirmwareUploader(unittest.TestCase):

    @patch("bin.ad2_firmwareupload.Firmware.upload")
    @patch("bin.ad2_firmwareupload.get_device")
    def test_upload_successful(self, mock_get_device, mock_upload):
        mock_dev = MagicMock()
        mock_get_device.return_value = mock_dev

        cli.upload_firmware_with_retries(mock_dev, "firmware.hex", debug=False)

        mock_upload.assert_called_once_with(mock_dev, "firmware.hex", debug=False)

    @patch("bin.ad2_firmwareupload.Firmware.upload", side_effect=Exception("fail"))
    @patch("bin.ad2_firmwareupload.get_device")
    def test_retry_logic(self, mock_get_device, mock_upload):
        mock_dev = MagicMock()
        mock_get_device.return_value = mock_dev

        with self.assertRaises(RuntimeError):
            cli.upload_firmware_with_retries(mock_dev, "firmware.hex", debug=False)

        self.assertEqual(mock_upload.call_count, cli.RETRIES)


if __name__ == "__main__":
    unittest.main()