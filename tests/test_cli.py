# tests/test_cli.py
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from matter_hub.cli import cli


def test_auth_displays_qr_and_saves_token():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.trigger_qr_login.return_value = "session_123"
    mock_client.exchange_token.side_effect = [None, {"access_token": "acc", "refresh_token": "ref"}]

    with patch("matter_hub.cli.MatterClient", return_value=mock_client), \
         patch("matter_hub.cli.save_config") as mock_save, \
         patch("matter_hub.cli.qrcode") as mock_qr, \
         patch("matter_hub.cli.time") as mock_time:
        result = runner.invoke(cli, ["auth"])

    assert result.exit_code == 0
    assert "認証成功" in result.output
    mock_save.assert_called_once()
