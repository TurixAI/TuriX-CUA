import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest


class FakeChatModel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def load_example_main():
    pynput = types.ModuleType("pynput")
    pynput.keyboard = types.ModuleType("pynput.keyboard")

    src = types.ModuleType("src")
    src.__path__ = []
    src.Agent = object
    src_controller = types.ModuleType("src.controller")
    src_controller.__path__ = []
    src_controller_service = types.ModuleType("src.controller.service")
    src_controller_service.Controller = object

    modules = {
        "pynput": pynput,
        "pynput.keyboard": pynput.keyboard,
        "src": src,
        "src.controller": src_controller,
        "src.controller.service": src_controller_service,
    }
    for module_name, class_name in (
        ("langchain_openai", "ChatOpenAI"),
        ("langchain_google_genai", "ChatGoogleGenerativeAI"),
        ("langchain_anthropic", "ChatAnthropic"),
        ("langchain_ollama", "ChatOllama"),
    ):
        module = types.ModuleType(module_name)
        setattr(module, class_name, FakeChatModel)
        modules[module_name] = module

    module_path = Path(__file__).parents[1] / "examples" / "main.py"
    spec = importlib.util.spec_from_file_location("turix_example_main", module_path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module


@pytest.fixture()
def example_main():
    return load_example_main()


def test_atlascloud_defaults_and_capabilities(example_main):
    with patch.dict("os.environ", {"ATLASCLOUD_API_KEY": "atlas-test"}, clear=True):
        llm = example_main.build_llm({"provider": "atlascloud"})

    assert llm.kwargs["model"] == "qwen/qwen3.5-flash"
    assert llm.kwargs["openai_api_key"] == "atlas-test"
    assert llm.kwargs["openai_api_base"] == "https://api.atlascloud.ai/v1"
    assert llm._turix_supports_tool_calling is True
    assert llm._turix_supports_response_format is False


def test_atlas_alias_honors_explicit_overrides(example_main):
    llm = example_main.build_llm(
        {
            "provider": "atlas",
            "api_key": "explicit-key",
            "model_name": "custom/model",
            "base_url": "https://example.test/v1",
            "temperature": 0.25,
            "max_tokens": 2048,
            "timeout": 30,
        }
    )

    assert llm.kwargs == {
        "model": "custom/model",
        "openai_api_key": "explicit-key",
        "openai_api_base": "https://example.test/v1",
        "temperature": 0.25,
        "max_tokens": 2048,
        "timeout": 30,
    }


def test_atlascloud_requires_provider_key(example_main):
    with (
        patch.dict("os.environ", {"OPENAI_API_KEY": "wrong-provider-key"}, clear=True),
        pytest.raises(ValueError, match="ATLASCLOUD_API_KEY"),
    ):
        example_main.build_llm({"provider": "atlascloud"})
