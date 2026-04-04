from pathlib import Path

PROMPT_VERSION = "v1"
PROMPTS_ROOT = Path(__file__).parent / "prompts" / PROMPT_VERSION


def load_prompt(name: str) -> str:
    path = PROMPTS_ROOT / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


RESEARCH_AGENT_PROMPT = load_prompt("research_agent")
DRAFTING_AGENT_PROMPT = load_prompt("drafting_agent")
