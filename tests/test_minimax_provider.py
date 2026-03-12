"""Unit tests for the MiniMax provider in build_llm."""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "examples"))

# Mock out heavy dependencies before importing main
sys.modules["pynput"] = MagicMock()
sys.modules["pynput.keyboard"] = MagicMock()
sys.modules["pyautogui"] = MagicMock()
sys.modules["src"] = MagicMock()
sys.modules["src.controller"] = MagicMock()
sys.modules["src.controller.service"] = MagicMock()

from main import build_llm


class TestMiniMaxProvider(unittest.TestCase):
    """Test MiniMax provider configuration in build_llm."""

    @patch("main.ChatOpenAI")
    def test_default_base_url(self, mock_chat):
        """MiniMax should use https://api.minimax.io/v1 by default."""
        mock_chat.return_value = MagicMock()
        build_llm({"provider": "minimax", "api_key": "test-key"})
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs["openai_api_base"], "https://api.minimax.io/v1")

    @patch("main.ChatOpenAI")
    def test_custom_base_url(self, mock_chat):
        """Custom base_url should override the default."""
        mock_chat.return_value = MagicMock()
        build_llm({
            "provider": "minimax",
            "api_key": "test-key",
            "base_url": "https://api.minimaxi.com/v1",
        })
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs["openai_api_base"], "https://api.minimaxi.com/v1")

    @patch("main.ChatOpenAI")
    def test_default_model_name(self, mock_chat):
        """Default model should be MiniMax-M2.5."""
        mock_chat.return_value = MagicMock()
        build_llm({"provider": "minimax", "api_key": "test-key"})
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs["model"], "MiniMax-M2.5")

    @patch("main.ChatOpenAI")
    def test_custom_model_name(self, mock_chat):
        """Custom model_name should be used."""
        mock_chat.return_value = MagicMock()
        build_llm({
            "provider": "minimax",
            "api_key": "test-key",
            "model_name": "MiniMax-M2.5-highspeed",
        })
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs["model"], "MiniMax-M2.5-highspeed")

    @patch("main.ChatOpenAI")
    def test_temperature_is_one(self, mock_chat):
        """MiniMax temperature should be 1.0."""
        mock_chat.return_value = MagicMock()
        build_llm({"provider": "minimax", "api_key": "test-key"})
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs["temperature"], 1.0)

    @patch.dict(os.environ, {"MINIMAX_API_KEY": "env-key"}, clear=False)
    @patch("main.ChatOpenAI")
    def test_env_api_key(self, mock_chat):
        """MINIMAX_API_KEY env var should be used when no api_key in config."""
        mock_chat.return_value = MagicMock()
        build_llm({"provider": "minimax"})
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs["openai_api_key"], "env-key")

    @patch("main.ChatOpenAI")
    def test_tool_calling_enabled(self, mock_chat):
        """MiniMax should have tool calling enabled."""
        mock_instance = MagicMock()
        mock_chat.return_value = mock_instance
        result = build_llm({"provider": "minimax", "api_key": "test-key"})
        self.assertTrue(getattr(result, "_turix_supports_tool_calling", False))

    @patch("main.ChatOpenAI")
    def test_response_format_disabled(self, mock_chat):
        """MiniMax should have response_format disabled."""
        mock_instance = MagicMock()
        mock_chat.return_value = mock_instance
        result = build_llm({"provider": "minimax", "api_key": "test-key"})
        self.assertFalse(getattr(result, "_turix_supports_response_format", True))


if __name__ == "__main__":
    unittest.main()
