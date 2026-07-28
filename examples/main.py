import os, sys, json, logging, argparse, asyncio, ctypes
from logging.handlers import RotatingFileHandler
from pathlib import Path
from pynput import keyboard

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

from src import Agent
from src.controller.service import Controller

# ---------- Utilities -------------------------------------------------------
def has_screen_capture_permission() -> bool:
    CoreGraphics = ctypes.cdll.LoadLibrary(
        "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
    )
    return bool(CoreGraphics.CGPreflightScreenCaptureAccess())

LOG_LEVEL_MAP = {
    "CRITICAL": logging.CRITICAL,
    "ERROR":    logging.ERROR,
    "WARNING":  logging.WARNING,
    "INFO":     logging.INFO,
    "DEBUG":    logging.DEBUG,
}

HOTKEY_ALIASES = {
    "command": "<cmd>",
    "cmd": "<cmd>",
    "shift": "<shift>",
    "control": "<ctrl>",
    "ctrl": "<ctrl>",
    "option": "<alt>",
    "alt": "<alt>",
    "opt": "<alt>",
}

def resolve_output_dir(cfg: dict, config_path: Path) -> Path:
    output_dir = (
        os.getenv("TURIX_OUTPUT_DIR")
        or cfg.get("output_dir")
        or cfg.get("agent", {}).get("output_dir")
    )
    if output_dir:
        path = Path(output_dir).expanduser()
        if not path.is_absolute():
            path = (Path(config_path).parent / path).resolve()
    else:
        path = (project_root / ".turix_tmp").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path

def resolve_artifact_path(raw_path: str | None, output_dir: Path) -> str | None:
    if not raw_path:
        return None
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = output_dir / path
    if path.parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)

def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config file {path} not found.")
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)

def normalize_hotkey(hotkey: str) -> str:
    if not hotkey:
        return ""
    parts = [p for p in hotkey.replace(" ", "").split("+") if p]
    normalized = []
    for part in parts:
        token = part.strip()
        lower = token.lower()
        if lower in HOTKEY_ALIASES:
            normalized.append(HOTKEY_ALIASES[lower])
        elif lower.startswith("<") and lower.endswith(">"):
            normalized.append(lower)
        else:
            normalized.append(lower)
    return "+".join(normalized)

def register_force_stop_hotkey(
    loop: asyncio.AbstractEventLoop,
    agent: Agent,
    agent_task: asyncio.Task,
    hotkey: str,
    log: logging.Logger,
):
    def _force_stop():
        log.warning("Force-stop hotkey pressed. Stopping agent now.")
        agent.stop("force-stop hotkey")
        if not agent_task.done():
            agent_task.cancel()

    def _on_activate():
        loop.call_soon_threadsafe(_force_stop)

    listener = keyboard.GlobalHotKeys({hotkey: _on_activate})
    listener.start()
    return listener


def configure_llm_capabilities(llm, *, supports_tool_calling: bool, supports_response_format: bool):
    setattr(llm, "_turix_supports_tool_calling", supports_tool_calling)
    setattr(llm, "_turix_supports_response_format", supports_response_format)
    return llm


def _merge_model_kwargs(cfg: dict, enable_thinking: bool | None = None) -> dict:
    model_kwargs = cfg.get("model_kwargs")
    if not isinstance(model_kwargs, dict):
        model_kwargs = {}
    else:
        model_kwargs = dict(model_kwargs)

    extra_body_merged = {}
    existing_extra_body = cfg.get("extra_body")
    if isinstance(existing_extra_body, dict) and existing_extra_body:
        extra_body_merged.update(existing_extra_body)

    chat_template_kwargs = cfg.get("chat_template_kwargs")
    if isinstance(chat_template_kwargs, dict):
        merged_chat_template_kwargs = dict(chat_template_kwargs)
    else:
        merged_chat_template_kwargs = {}

    if enable_thinking is not None:
        merged_chat_template_kwargs["enable_thinking"] = bool(enable_thinking)

    if merged_chat_template_kwargs:
        extra_body_merged["chat_template_kwargs"] = merged_chat_template_kwargs

    if extra_body_merged:
        prebound_extra = model_kwargs.get("extra_body")
        if isinstance(prebound_extra, dict):
            merged_extra = dict(prebound_extra)
            merged_extra.update(extra_body_merged)
            model_kwargs["extra_body"] = merged_extra
        else:
            model_kwargs["extra_body"] = extra_body_merged

    return model_kwargs


def build_openai_compatible_llm(
    *,
    model_name: str,
    api_key: str | None,
    base_url: str | None,
    temperature: float = 0.1,
    supports_tool_calling: bool = True,
    supports_response_format: bool = True,
    model_kwargs: dict | None = None,
    max_tokens: int | None = None,
    timeout: float | int | None = None,
):
    if not model_name:
        raise ValueError("OpenAI-compatible provider requires 'model_name'.")
    kwargs = {
        "model": model_name,
        "openai_api_key": api_key,
        "temperature": temperature,
    }
    if base_url:
        kwargs["openai_api_base"] = base_url
    if model_kwargs:
        kwargs["model_kwargs"] = model_kwargs
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if timeout is not None:
        kwargs["timeout"] = timeout
    llm = ChatOpenAI(**kwargs)
    return configure_llm_capabilities(
        llm,
        supports_tool_calling=supports_tool_calling,
        supports_response_format=supports_response_format,
    )

def build_llm(cfg: dict, *, enable_thinking: bool | None = None):
    provider = cfg["provider"].lower()
    api_key  = cfg.get("api_key") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
    model_name = cfg.get("model_name")
    base_url = cfg.get("base_url")
    model_kwargs = _merge_model_kwargs(cfg, enable_thinking=enable_thinking)
    max_tokens = cfg.get("max_tokens")
    timeout = cfg.get("timeout")

    if provider in {"atlascloud", "atlas"}:
        atlas_api_key = (
            cfg.get("api_key")
            or os.getenv("ATLASCLOUD_API_KEY")
            or os.getenv("ATLAS_CLOUD_API_KEY")
        )
        if not atlas_api_key:
            raise ValueError(
                "Atlas Cloud provider requires 'api_key' or ATLASCLOUD_API_KEY."
            )
        return build_openai_compatible_llm(
            model_name=model_name or "qwen/qwen3.5-flash",
            api_key=atlas_api_key,
            base_url=base_url or "https://api.atlascloud.ai/v1",
            temperature=cfg.get("temperature", 0.1),
            supports_tool_calling=True,
            supports_response_format=False,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider == "turix":
        if not base_url:
            raise ValueError("OpenAI‑compatible provider requires 'base_url'.")
        return build_openai_compatible_llm(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.1,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider == "deepseek":
        return build_openai_compatible_llm(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://api.deepseek.com/v1",
            temperature=0.1,
            supports_tool_calling=False,
            supports_response_format=False,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider == "minimax":
        return build_openai_compatible_llm(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://api.minimax.chat/v1",
            temperature=0.1,
            supports_tool_calling=False,
            supports_response_format=False,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider == "kimi":
        return build_openai_compatible_llm(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://api.moonshot.cn/v1",
            temperature=0.1,
            supports_tool_calling=True,
            supports_response_format=False,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider == "ollama":
        if not model_name:
            raise ValueError("Ollama provider requires 'model_name'.")
        ollama_kwargs = {"model": model_name, "temperature": 0.3}
        if base_url:
            ollama_kwargs["base_url"] = base_url
        llm = ChatOllama(**ollama_kwargs)
        return configure_llm_capabilities(
            llm,
            supports_tool_calling=bool(cfg.get("supports_tool_calling", True)),
            # Disabled by default because some Ollama model/runtime combos fail with:
            # "failed to load model vocabulary required for format"
            supports_response_format=bool(cfg.get("supports_response_format", False)),
        )

    if provider == "google_flash":
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", api_key=api_key, temperature=0.3
        )
    
    if provider == "gpt":
        return build_openai_compatible_llm(
            model_name=model_name or "gpt-4.1-mini",
            api_key=api_key,
            base_url=base_url,
            temperature=cfg.get("temperature", 0.3),
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider == "google_pro":
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-pro", api_key=api_key, temperature=0.3
        )

    if provider == "anthropic":
        return ChatAnthropic(model="claude-4-opus", api_key=api_key, temperature=0.3)

    raise ValueError(f"Unknown llm provider '{provider}'")

# ---------- Main ------------------------------------------------------------
def main(config_path: str = "config.json"):
    # Make config path relative to script location if it's a relative path
    if not Path(config_path).is_absolute():
        config_path = Path(__file__).parent / config_path
    
    cfg = load_config(Path(config_path))
    output_dir = resolve_output_dir(cfg, Path(config_path))
    brain_enable_thinking = cfg.get("brain_enable_thinking")
    if not isinstance(brain_enable_thinking, bool):
        thinking_cfg = cfg.get("thinking")
        if isinstance(thinking_cfg, dict) and isinstance(thinking_cfg.get("brain"), bool):
            brain_enable_thinking = thinking_cfg.get("brain")
        else:
            brain_enable_thinking = False

    # --- Logging -----------------------------------------------------------
    log_level_str = cfg.get("logging_level", "DEBUG").upper()
    use_plan = cfg.get("agent", {}).get("use_plan", False)
    logging_level = LOG_LEVEL_MAP.get(log_level_str, logging.DEBUG)
    
    # Configure root logger first
    logging.basicConfig(
        level=logging_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Console output
            RotatingFileHandler(str(output_dir / "logging.log"), maxBytes=20 * 1024 * 1024, backupCount=3)
        ],
        force=True,
    )
    
    # Set up specific logger
    log = logging.getLogger("turix")
    log.handlers.clear()
    log.propagate = True
    log.setLevel(logging_level)
    
    # Also set logging for other relevant modules
    logging.getLogger("src").setLevel(logging_level)
    logging.getLogger("src.agent").setLevel(logging_level)
    logging.getLogger("src.agent.message_manager").setLevel(logging_level)
    
    print(f"Logging level set to: {log_level_str}")

    # --- Permissions check -------------------------------------------------
    if not has_screen_capture_permission():
        print(
            "Please enable screen recording permission for this script in "
            "System Settings ▸ Privacy & Security ▸ Screen Recording."
        )
        sys.exit(1)

    # --- Build LLM & Agent --------------------------------------------------
    brain_llm = build_llm(cfg["brain_llm"], enable_thinking=brain_enable_thinking)
    actor_llm = build_llm(cfg["actor_llm"], enable_thinking=False)
    memory_llm = build_llm(cfg["memory_llm"], enable_thinking=False)
    if use_plan:
        planner_llm = build_llm(cfg["planner_llm"], enable_thinking=True)
    else:
        planner_llm = None
    log.info(
        "Thinking config => brain=%s, actor=%s, memory=%s, planner=%s",
        brain_enable_thinking,
        False,
        False,
        bool(use_plan),
    )
    agent_cfg = cfg["agent"]
    skills_dir = agent_cfg.get("skills_dir")
    if skills_dir:
        skills_dir_path = Path(skills_dir)
        if not skills_dir_path.is_absolute():
            config_relative = (Path(config_path).parent / skills_dir_path).resolve()
            if config_relative.exists():
                skills_dir_path = config_relative
            else:
                project_relative = (project_root / skills_dir_path).resolve()
                skills_dir_path = project_relative
        skills_dir = skills_dir_path
    controller = Controller()
    raw_hotkey = agent_cfg.get("force_stop_hotkey")
    force_stop_hotkey = normalize_hotkey(raw_hotkey) if raw_hotkey else ""
    save_brain_conversation_path = resolve_artifact_path(
        agent_cfg.get("save_brain_conversation_path"), output_dir
    )
    save_actor_conversation_path = resolve_artifact_path(
        agent_cfg.get("save_actor_conversation_path"), output_dir
    )
    save_planner_conversation_path = resolve_artifact_path(
        agent_cfg.get("save_planner_conversation_path"), output_dir
    )
    memory_budget_tokens = agent_cfg.get("memory_budget_tokens", agent_cfg.get("memory_budget", 500))
    summary_memory_budget_tokens = agent_cfg.get(
        "summary_memory_budget_tokens",
        agent_cfg.get("summary_memory_budget"),
    )

    agent = Agent(
        task                    = agent_cfg["task"],
        brain_llm               = brain_llm,
        actor_llm               = actor_llm,
        planner_llm             = planner_llm,
        memory_llm              = memory_llm,
        memory_budget           = memory_budget_tokens,
        summary_memory_budget   = summary_memory_budget_tokens,
        controller              = controller,
        use_ui                  = agent_cfg.get("use_ui", False),
        use_search              = agent_cfg.get("use_search", True),
        use_skills              = agent_cfg.get("use_skills", False),
        skills_dir              = str(skills_dir) if skills_dir else None,
        skills_max_chars         = agent_cfg.get("skills_max_chars", 4000),
        max_actions_per_step    = agent_cfg.get("max_actions_per_step", 5),
        resume                  = agent_cfg.get("resume", False),
        agent_id                = agent_cfg.get("agent_id"),
        save_brain_conversation_path  = save_brain_conversation_path,
        save_brain_conversation_path_encoding = agent_cfg.get("save_brain_conversation_path_encoding", "utf-8"),
        save_actor_conversation_path  = save_actor_conversation_path,
        save_actor_conversation_path_encoding = agent_cfg.get("save_actor_conversation_path_encoding", "utf-8"),
        save_planner_conversation_path = save_planner_conversation_path,
        save_planner_conversation_path_encoding = agent_cfg.get("save_planner_conversation_path_encoding", "utf-8"),
        artifacts_dir           = str(output_dir),
    )

    async def runner():
        loop = asyncio.get_running_loop()
        agent_task = asyncio.create_task(agent.run(max_steps=agent_cfg.get("max_steps", 100)))
        listener = None
        if force_stop_hotkey:
            try:
                listener = register_force_stop_hotkey(loop, agent, agent_task, force_stop_hotkey, log)
                log.info("Force-stop hotkey registered: %s", force_stop_hotkey)
            except Exception:
                log.exception("Failed to register force-stop hotkey: %s", raw_hotkey)
        try:
            await agent_task
        except asyncio.CancelledError:
            log.warning("Agent task cancelled.")
        finally:
            if listener:
                listener.stop()

    asyncio.run(runner())

# ---------- CLI -------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the TuriX agent.")
    parser.add_argument(
        "-c", "--config", default="config.json", help="Path to configuration JSON file"
    )
    args = parser.parse_args()
    main(args.config)
