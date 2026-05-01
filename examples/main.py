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
        token = part.strip().lower()
        if token in HOTKEY_ALIASES:
            normalized.append(HOTKEY_ALIASES[token])
        elif token.startswith("<") and token.endswith(">"):
            normalized.append(token)
        else:
            normalized.append(token)
    return "+".join(normalized)

def request_agent_force_stop(agent: Agent, log: logging.Logger):
    """
    Compatible force-stop path for both newer and legacy Agent implementations.
    """
    stop_fn = getattr(agent, "stop", None)
    if callable(stop_fn):
        try:
            stop_fn("force-stop hotkey")
        except TypeError:
            stop_fn()
        return

    if hasattr(agent, "_stopped"):
        setattr(agent, "_stopped", True)
        log.warning("Force-stop fallback used: set agent._stopped=True")

def register_force_stop_hotkey(
    loop: asyncio.AbstractEventLoop,
    agent: Agent,
    agent_task: asyncio.Task,
    hotkey: str,
    log: logging.Logger,
):
    def _force_stop():
        log.warning("Force-stop hotkey pressed. Stopping agent now.")
        request_agent_force_stop(agent, log)
        if not agent_task.done():
            agent_task.cancel()

    def _on_activate():
        loop.call_soon_threadsafe(_force_stop)

    listener = keyboard.GlobalHotKeys({hotkey: _on_activate})
    listener.start()
    return listener

def build_openai_compatible_llm(
    *,
    model_name: str,
    api_key: str | None,
    base_url: str | None,
    temperature: float = 0.3,
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
    return ChatOpenAI(**kwargs)

def build_llm(cfg: dict, enable_thinking: bool | None = None):
    provider = cfg["provider"].lower()
    api_key  = cfg.get("api_key") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
    model_name = cfg.get("model_name")
    base_url = cfg.get("base_url")
    temperature = cfg.get("temperature", 0.3)
    max_tokens = cfg.get("max_tokens")
    timeout = cfg.get("timeout")
    # Optional passthrough for OpenAI-compatible backends.
    # Useful for disabling provider-specific "thinking/reasoning" modes.
    model_kwargs = cfg.get("model_kwargs")
    if not isinstance(model_kwargs, dict):
        model_kwargs = {}
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
        # Global switch: enforce the same thinking mode on all model configs.
        merged_chat_template_kwargs["enable_thinking"] = bool(enable_thinking)
    if merged_chat_template_kwargs:
        extra_body_merged["chat_template_kwargs"] = merged_chat_template_kwargs
    if extra_body_merged:
        prebound_extra = model_kwargs.get("extra_body")
        if isinstance(prebound_extra, dict):
            merged = dict(prebound_extra)
            merged.update(extra_body_merged)
            model_kwargs["extra_body"] = merged
        else:
            model_kwargs["extra_body"] = extra_body_merged

    if provider == "turix":
        if not base_url:
            raise ValueError("OpenAI‑compatible provider requires 'base_url'.")
        return build_openai_compatible_llm(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider == "deepseek":
        return build_openai_compatible_llm(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://api.deepseek.com/v1",
            temperature=temperature,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider == "minimax":
        return build_openai_compatible_llm(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://api.minimax.chat/v1",
            temperature=temperature,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider == "kimi":
        return build_openai_compatible_llm(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://api.moonshot.cn/v1",
            temperature=temperature,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider == "ollama":
        if not model_name:
            raise ValueError("Ollama provider requires 'model_name'.")
        ollama_kwargs = {"model": model_name, "temperature": temperature}
        if base_url:
            ollama_kwargs["base_url"] = base_url
        return ChatOllama(**ollama_kwargs)

    if provider == "google_flash":
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", api_key=api_key, temperature=temperature
        )
    
    if provider in {"gpt", "openai"}:
        return build_openai_compatible_llm(
            model_name=(model_name or "gpt-4.1-mini"),
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    if provider == "google_pro":
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-pro", api_key=api_key, temperature=temperature
        )

    if provider == "anthropic":
        return ChatAnthropic(
            model=model_name or "claude-4-opus",
            api_key=api_key,
            temperature=temperature
        )

    raise ValueError(f"Unknown llm provider '{provider}'")

# ---------- Main ------------------------------------------------------------
def main(config_path: str = "config.json"):
    # Make config path relative to script location if it's a relative path
    if not Path(config_path).is_absolute():
        config_path = Path(__file__).parent / config_path
    
    cfg = load_config(Path(config_path))

    # --- Logging -----------------------------------------------------------
    log_level_str = cfg.get("logging_level", "DEBUG").upper()
    logging_level = LOG_LEVEL_MAP.get(log_level_str, logging.DEBUG)
    
    # Configure root logger first
    logging.basicConfig(
        level=logging_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Console output
            RotatingFileHandler("logging.log", maxBytes=20 * 1024 * 1024, backupCount=3)
        ],
        force=True,
    )
    
    # Set up specific logger
    log = logging.getLogger("turix")
    # src/__init__.py calls setup_logging() during import and may leave turix logger
    # detached from root handlers; reset so file handler receives turix logs too.
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
    agent_cfg = cfg["agent"]
    raw_hotkey = agent_cfg.get("force_stop_hotkey", "command+shift+2")
    force_stop_hotkey = normalize_hotkey(raw_hotkey)
    global_enable_thinking = cfg.get("enable_thinking")
    if isinstance(global_enable_thinking, bool):
        enable_thinking = global_enable_thinking
    else:
        enable_thinking = None

    llm = build_llm(cfg["llm"], enable_thinking=enable_thinking)
    use_planner = agent_cfg.get("use_planner", True)
    planner_llm = build_llm(cfg["planner_llm"], enable_thinking=enable_thinking) if use_planner else None
    memory_llm_cfg = cfg.get("memory_llm")
    memory_llm = build_llm(memory_llm_cfg, enable_thinking=enable_thinking) if memory_llm_cfg else None
    controller = Controller()
    save_llm_conversation_path = agent_cfg.get("save_llm_conversation_path")
    save_llm_conversation_path_encoding = agent_cfg.get(
        "save_llm_conversation_path_encoding", "utf-8"
    )

    agent = Agent(
        task                    = agent_cfg["task"],
        llm                     = llm,
        memory_llm              = memory_llm,
        planner_llm             = planner_llm,
        use_turix               = agent_cfg.get("use_turix", True),
        short_memory_len        = agent_cfg.get("short_memory_len", 5),
        memory_budget           = agent_cfg.get("memory_budget", 500),
        summary_memory_budget   = agent_cfg.get("summary_memory_budget"),
        controller              = controller,
        use_ui                  = agent_cfg.get("use_ui", False),
        max_actions_per_step    = agent_cfg.get("max_actions_per_step", 5),
        resume                  = agent_cfg.get("resume", False),
        agent_id                = agent_cfg.get("agent_id"),
        save_llm_conversation_path = save_llm_conversation_path,
        save_llm_conversation_path_encoding = save_llm_conversation_path_encoding,
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
    os.makedirs("images", exist_ok=True)
    parser = argparse.ArgumentParser(description="Run the TuriX agent.")
    parser.add_argument(
        "-c", "--config", default="config.json", help="Path to configuration JSON file"
    )
    args = parser.parse_args()
    main(args.config)
