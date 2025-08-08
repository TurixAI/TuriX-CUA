import asyncio, traceback, sys, os, logging
from fastmcp import FastMCP
from src.agent.service import Agent
from langchain_openai import ChatOpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)

def build_llm_from_env():
    """
    Convert the ENV passed by the MCP launcher into a langchain LLM instance.
    Extend this if you want to support more back‑ends.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    model       = os.getenv("LLM_MODEL",  "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMP", "0"))
    api_base    = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    api_key     = os.getenv("OPENAI_API_KEY")

    # Provider‑specific branches ───────────────────────────
    if provider in {"openai", "turix", "azure"}:
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY for provider '%s'" % provider)
        return ChatOpenAI(
            model=model,
            openai_api_base=api_base,
            openai_api_key=api_key,
            temperature=temperature,
        )

    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(
            model=model,
            base_url=os.getenv("OLLAMA_BASE", "http://localhost:default"),
            temperature=temperature,
        )
    
    elif provider in {"gemini", "google"}:
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY / GOOGLE_API_KEY for Gemini provider")
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
        )
    
    elif provider in {"anthropic", "claude"}:
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        api_base = os.getenv("ANTHROPIC_API_BASE", None)
        if not api_key:
            raise RuntimeError("Missing ANTHROPIC_API_KEY for Anthropic provider")
        return ChatAnthropic(
            model=model,
            anthropic_api_key=api_key,
            anthropic_api_base=api_base,
            temperature=temperature,
        )
    
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER='{provider}'")
    
service = FastMCP('TuriX MCP Server')
TIMEOUT_S = int(os.getenv("MCP_TIMEOUT_SEC", 600))

@service.tool()
async def run_task(task: str) -> str:
    llm = build_llm_from_env()
    agent = Agent(
        task=task,
        llm=llm,
        short_memory_len=3,
        max_failures=5,
        running_mcp = True
    )

    try:
        result = await asyncio.wait_for(
            agent.run_MCP(max_steps=40),
            timeout=TIMEOUT_S,
        )
        return result
    
    except asyncio.TimeoutError:
        # hit the TIMEOUT_S
        return "Exceeding the time set by user"

    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        return f"failed executing: {exc}"
    

if __name__ == "__main__":
    service.run(transport="stdio")
