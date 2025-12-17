import os, sys, json, logging, argparse, asyncio, ctypes, torch
from logging.handlers import RotatingFileHandler
from pathlib import Path
import numpy as np
from PIL import Image
from torchvision import transforms


# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

from src import Agent
from src.controller.service import Controller
from src.dinov3 import vision_transformer as dinov3_ 

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
    model_name = cfg.get("model_name")
    base_url = cfg.get("base_url")
    timeout = None if "timeout" not in cfg else cfg["timeout"]
    max_retries = None if "max_retries" not in cfg else cfg["max_retries"]

    if provider == "turix":
        if not base_url:
            raise ValueError("OpenAI‑compatible provider requires 'base_url'.")
        return ChatOpenAI(
            model=model_name,
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
    
    if provider == "openai":
        return OpenAIEmbeddings(
            model=model_name,  
            openai_api_base=base_url, 
            openai_api_key=api_key,
            max_retries=max_retries,  
            timeout=timeout  
        )

    raise ValueError(f"Unknown llm provider '{provider}'")

class DynamicImageMatcher:
    def __init__(self, cfg: dict):

        self.img_size = cfg.get("img_size")
        self.pretrained = cfg.get("pretrained")
        self.feature_dim = cfg.get("feature_dim")
        self.model_weight_path = cfg.get("weight_path")

        self.id_to_name = {}
        self.next_id = 0
        self.transforms= transforms.Compose([
        transforms.Resize((self.img_size, self.img_size)), 
        transforms.ToTensor(),       
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]), 
        ])

        self.build_model()
        
    def build_model(self):
        self.model = dinov3_.DinoVisionTransformer(
        img_size=self.img_size,
        layerscale_init=1,
        )
        
        if self.pretrained:
            model_dict = self.model.state_dict()
            state_dit = torch.load(self.model_weight_path, map_location='mps',weights_only=True)
            model_dict.update(state_dit.items())
            self.model.load_state_dict(model_dict)
            self.model = self.model.eval()
        return self.model
    
    def _get_image_embedding(self, image_path: str) -> np.ndarray:

        image = Image.open(image_path).convert('RGB')
        input_tensor = self.transforms(image).unsqueeze(0) 
        with torch.no_grad():
            embedding = self.model(input_tensor)
        
        embedding_np = embedding.squeeze().numpy()
        return embedding_np

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
    brain_llm = build_llm(cfg["brain_llm"])
    actor_llm = build_llm(cfg["actor_llm"])
    planner_llm = build_llm(cfg["planner_llm"])
    agent_cfg = cfg["agent"]
    controller = Controller()
    screenshot_features_extractor = DynamicImageMatcher(cfg["screenshot_features_extractor"])
    embed_llm = build_llm(cfg["embed_llm"])


    # task：
    # "open Chrome, go to github, and search for turix-cua in the github webpage. Enter the TuriX-CUA repository, and star it.",
    # "用safari去苹果官网帮我找到手机iphone 手机的最新价格信息，用record_info进行记录（型号和价格），然后写成一个pages文档,保存成pdf文件，重命名后保存到桌面 然后用微信发给 pyk"
    agent = Agent(
        task                    = agent_cfg["task"],
        brain_llm               = brain_llm,
        actor_llm               = actor_llm,
        # planner_llm             = planner_llm,
        planner_llm             =  None,
        embed_llm               = embed_llm,
        short_memory_len        = agent_cfg.get("short_memory_len", 5),
        controller              = controller,
        use_ui                  = agent_cfg.get("use_ui", False),
        max_actions_per_step    = agent_cfg.get("max_actions_per_step", 5),
        save_brain_conversation_path  = agent_cfg.get("save_brain_conversation_path"),
        save_brain_conversation_path_encoding = agent_cfg.get("save_brain_conversation_path_encoding", "utf-8"),
        save_actor_conversation_path  = agent_cfg.get("save_actor_conversation_path"),
        save_actor_conversation_path_encoding = agent_cfg.get("save_actor_conversation_path_encoding", "utf-8"),
        # the below params for knoewlege base retirval
        knowledge_base_json     = agent_cfg.get("knowledge_base_json"),
        screenshot_features_extractor = screenshot_features_extractor,
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