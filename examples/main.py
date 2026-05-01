import os
os.environ["ANONYMIZED_TELEMETRY"] = "false"
import sys
import json
import logging
import argparse
import asyncio
import glob
import shutil
import platform
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load config early to set logging level before importing src
def load_config_early(path: Path) -> dict:
    """Load configuration from JSON file early to set logging level."""
    if not path.exists():
        raise FileNotFoundError(f"Config file {path} not found.")
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)

# Set logging level environment variable before importing src
config_path = Path(__file__).parent / "config.json"
if config_path.exists():
    early_cfg = load_config_early(config_path)
    logging_level = early_cfg.get("logging_level", "INFO").lower()
    os.environ["turix_LOGGING_LEVEL"] = logging_level

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

from src import Agent
from src.controller.service import Controller

# ---------- Utilities -------------------------------------------------------
LOG_LEVEL_MAP = {
    "CRITICAL": logging.CRITICAL,
    "ERROR":    logging.ERROR,
    "WARNING":  logging.WARNING,
    "INFO":     logging.INFO,
    "DEBUG":    logging.DEBUG,
}

def load_config(path: Path) -> dict:
    """Load configuration from JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Config file {path} not found.")
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)

def cleanup_previous_runs(working_dir_base: str):
    """Clean up logs and screenshots from previous runs, moving certain files to a working directory."""
    # Files to move and delete
    move_patterns = ['training_data.jsonl','training_data_cv.jsonl', 'images', 'evaluation_data.jsonl','evaluation_data_cv.jsonl']
    delete_patterns = [
        'ui_tree.log',
        'llm_interactions.log_agent_*.txt',
        'llm_interactions.log_evaluator_*.txt',
    ]

    current_dir = os.getcwd()

    # Find unique working directory name
    n = 1
    working_dir = f"{working_dir_base}_{n}"
    while os.path.exists(working_dir):
        n += 1
        working_dir = f"{working_dir_base}_{n}"

    # Create working directory
    os.makedirs(working_dir, exist_ok=True)

    # Move specified files/directories
    for pattern in move_patterns:
        matches = glob.glob(os.path.join(current_dir, pattern))
        for match in matches:
            try:
                dest = os.path.join(working_dir, os.path.basename(match))
                shutil.move(match, dest)
                print(f"Moved: {match} -> {dest}")
            except Exception as e:
                print(f"Error moving {match}: {e}")

    # Delete remaining specified files
    for pattern in delete_patterns:
        files = glob.glob(os.path.join(current_dir, pattern))
        for file in files:
            try:
                os.remove(file)
                print(f"Deleted: {file}")
            except Exception as e:
                print(f"Error deleting {file}: {e}")

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

def build_llm(cfg: dict):
    """Build LLM based on configuration."""
    provider = cfg["provider"].lower()
    api_key = cfg.get("api_key") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = cfg.get("base_url")
    model = cfg.get("model_name", "turix-model")
    temperature = cfg.get("temperature", 0.3)
    max_tokens = cfg.get("max_tokens")
    timeout = cfg.get("timeout")
    model_kwargs = cfg.get("model_kwargs")
    if not isinstance(model_kwargs, dict):
        model_kwargs = {}
    extra_body_merged = {}
    existing_extra_body = cfg.get("extra_body")
    if isinstance(existing_extra_body, dict) and existing_extra_body:
        extra_body_merged.update(existing_extra_body)
    chat_template_kwargs = cfg.get("chat_template_kwargs")
    if isinstance(chat_template_kwargs, dict) and chat_template_kwargs:
        extra_body_merged["chat_template_kwargs"] = dict(chat_template_kwargs)
    if extra_body_merged:
        prebound_extra = model_kwargs.get("extra_body")
        if isinstance(prebound_extra, dict):
            merged_extra = dict(prebound_extra)
            merged_extra.update(extra_body_merged)
            model_kwargs["extra_body"] = merged_extra
        else:
            model_kwargs["extra_body"] = extra_body_merged

    if provider == "turix":
        if not base_url:
            raise ValueError("Turix provider requires 'base_url'.")
        return build_openai_compatible_llm(
            model_name=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    elif provider == "deepseek":
        return build_openai_compatible_llm(
            model_name=model,
            api_key=api_key,
            base_url=base_url or "https://api.deepseek.com/v1",
            temperature=temperature,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    elif provider == "minimax":
        return build_openai_compatible_llm(
            model_name=model,
            api_key=api_key,
            base_url=base_url or "https://api.minimax.chat/v1",
            temperature=temperature,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    elif provider == "kimi":
        return build_openai_compatible_llm(
            model_name=model,
            api_key=api_key,
            base_url=base_url or "https://api.moonshot.cn/v1",
            temperature=temperature,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    elif provider == "google_pro_stable":
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-pro-preview-05-06",
            api_key=api_key,
            temperature=temperature
        )

    elif provider == "google_flash":
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            api_key=api_key,
            temperature=temperature
        )
    
    elif provider in {"openai", "gpt"}:
        return build_openai_compatible_llm(
            model_name=model if provider == "openai" else (model or "gpt-4.1-mini"),
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            model_kwargs=model_kwargs,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    elif provider == "anthropic":
        return ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=temperature
        )

    else:
        raise ValueError(f"Unknown llm provider '{provider}'")

def setup_logging(logging_level: str):
    """Acknowledge logging configuration (actual setup is done in src.logging_config)."""
    log_level_str = logging_level.upper()
    print(f"Logging level set to: {log_level_str} (configured via turix_LOGGING_LEVEL environment variable)")


# ---------- Main ------------------------------------------------------------
def main(config_path: str = "config.json"):
    """Main function to run the agent."""
    # Check if running on Windows
    if platform.system() != "Windows":
        print("This script is designed for Windows only.")
        sys.exit(1)

    # Make config path relative to script location if it's a relative path
    if not Path(config_path).is_absolute():
        config_path = Path(__file__).parent / config_path
    
    cfg = load_config(Path(config_path))
    global_enable_thinking = cfg.get("enable_thinking")
    if isinstance(global_enable_thinking, bool):
        for section_name in ("llm", "planner_llm", "memory_llm"):
            section = cfg.get(section_name)
            if isinstance(section, dict):
                ctk = section.get("chat_template_kwargs")
                if isinstance(ctk, dict):
                    ctk = dict(ctk)
                else:
                    ctk = {}
                ctk["enable_thinking"] = bool(global_enable_thinking)
                section["chat_template_kwargs"] = ctk
    
    # Update environment variable if different config was passed
    current_logging_level = cfg.get("logging_level", "INFO").lower()
    if os.environ.get("turix_LOGGING_LEVEL") != current_logging_level:
        os.environ["turix_LOGGING_LEVEL"] = current_logging_level
        print(f"Updated logging level to: {current_logging_level.upper()}")

    # --- Logging -----------------------------------------------------------
    setup_logging(cfg.get("logging_level", "DEBUG"))
    log_level_str = cfg.get("logging_level", "DEBUG").upper()
    logging_level = LOG_LEVEL_MAP.get(log_level_str, logging.DEBUG)
    logging.basicConfig(
        level=logging_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler("logging.log", maxBytes=20 * 1024 * 1024, backupCount=3),
        ],
        force=True,
    )
    turix_logger = logging.getLogger("turix")
    turix_logger.handlers.clear()
    turix_logger.propagate = True
    turix_logger.setLevel(logging_level)
    logging.getLogger("src").setLevel(logging_level)
    logging.getLogger("src.agent").setLevel(logging_level)
    logging.getLogger("src.agent.message_manager").setLevel(logging_level)

    # --- Cleanup previous runs ---------------------------------------------
    if cfg.get("cleanup_previous_runs", True):
        working_dir_base = cfg.get("working_dir_base", "Your_directory_name")
        try:
            cleanup_previous_runs(working_dir_base)
        except Exception as e:
            pass
    # --- Build LLM & Agent --------------------------------------------------
    agent_cfg = cfg["agent"]
    llm = build_llm(cfg["llm"])
    use_planner = agent_cfg.get("use_planner", True)
    planner_llm = build_llm(cfg["planner_llm"]) if use_planner else None
    memory_llm_cfg = cfg.get("memory_llm")
    memory_llm = build_llm(memory_llm_cfg) if memory_llm_cfg else None
    controller = Controller()
    save_llm_conversation_path = agent_cfg.get("save_llm_conversation_path")
    save_llm_conversation_path_encoding = agent_cfg.get(
        "save_llm_conversation_path_encoding", "utf-8"
    )

    # Create images directory
    os.makedirs("images", exist_ok=True)

    agent = Agent(
        task=agent_cfg["task"],
        llm=llm,
        planner_llm=planner_llm,
        use_turix=agent_cfg.get("use_turix", True),
        short_memory_len=agent_cfg.get("short_memory_len", 5),
        controller=controller,
        use_ui=agent_cfg.get("use_ui", False),
        max_actions_per_step=agent_cfg.get("max_actions_per_step", 5),
        resume=agent_cfg.get("resume", False),
        agent_id=agent_cfg.get("agent_id"),
        save_llm_conversation_path=save_llm_conversation_path,
        save_llm_conversation_path_encoding=save_llm_conversation_path_encoding,
        memory_llm=memory_llm,
    )

    async def runner():
        await agent.run(max_steps=agent_cfg.get("max_steps", 100))

    asyncio.run(runner())

# ---------- CLI -------------------------------------------------------------
if __name__ == "__main__":
    os.makedirs("images", exist_ok=True)
    parser = argparse.ArgumentParser(description="Run the TuriX agent on Windows.")
    parser.add_argument(
        "-c", "--config", default="config.json", 
        help="Path to configuration JSON file"
    )
    args = parser.parse_args()
    main(args.config)
