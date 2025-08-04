import os, sys, json, logging, argparse, asyncio, ctypes
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

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

def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config file {path} not found.")
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)

def build_llm(cfg: dict):
    provider = cfg["provider"].lower()
    api_key  = cfg.get("api_key") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = cfg.get("base_url")

    if provider == "turix":
        if not base_url:
            raise ValueError("OpenAI‑compatible provider requires 'base_url'.")
        return ChatOpenAI(
            model="turix-model",
            openai_api_base=base_url,
            openai_api_key=api_key,
            temperature=0.3,
        )

    if provider == "google_flash":
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", api_key=api_key, temperature=0.3
        )
    
    if provider == "gpt":
        return ChatOpenAI(
            model="gpt-4.1-mini", api_key=api_key, temperature=0.3
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
        ]
    )
    
    # Set up specific logger
    log = logging.getLogger("turix")
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
    llm = build_llm(cfg["llm"])
    agent_cfg = cfg["agent"]
    controller = Controller()

    agent = Agent(
        task                    = agent_cfg["task"],
        llm                     = llm,
        use_turix               = agent_cfg.get("use_turix", True),
        short_memory_len        = agent_cfg.get("short_memory_len", 5),
        controller              = controller,
        use_ui                  = agent_cfg.get("use_ui", False),
        max_actions_per_step    = agent_cfg.get("max_actions_per_step", 5),
        save_conversation_path  = agent_cfg.get("save_conversation_path"),
        save_conversation_path_encoding = agent_cfg.get("save_conversation_path_encoding", "utf-8"),
    )

    async def runner():
        await agent.run(max_steps=agent_cfg.get("max_steps", 100))

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