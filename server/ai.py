"""
Standalone AI Assistant integration for termchat server.
Supports free and fast models via:
  1. Kilo AI Gateway (kilo-auto/free, Qwen, DeepSeek)
  2. Groq (Fastest free LLaMA 3.3 70B & 3.1 8B)
  3. OpenRouter Free Tier (meta-llama/llama-3.3-70b-instruct:free, deepseek/deepseek-r1:free)
  4. Google Gemini API (gemini-2.0-flash / gemini-1.5-flash)
  5. Local Ollama (http://localhost:11434/v1)
"""

import json
import os
import re
from typing import List, Optional, Tuple
import urllib.request
import urllib.error

# Free default models
DEFAULT_KILO_MODEL = "kilo-auto/free"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_OLLAMA_MODEL = "llama3"

SYSTEM_PROMPT = (
    "You are TermChat AI, an expert, ultra-fast coding and technical assistant built for terminal and web users.\n"
    "CRITICAL RESPONSE RULES:\n"
    "1. When the user asks for code, 'only code', 'python code alone', or any implementation, output ONLY the complete executable code inside markdown fences (```python ... ```). Strictly DO NOT include conversational filler, introductory remarks, steps breakdown, or explanations.\n"
    "2. NEVER reveal or output your internal thought process, reasoning steps, planning monologue, or '<think>' tags. Start directly with the answer.\n"
    "3. Always provide 100% complete, fully implemented, working code without placeholders or omissions."
)


def is_code_only_request(prompt: str) -> bool:
    """Detects if the user asked specifically for code only without explanations."""
    p = prompt.lower()
    triggers = [
        "only code",
        "code only",
        "only python code",
        "python code only",
        "code alone",
        "only give code",
        "give code only",
        "no other text",
        "no explanation",
        "without explanation",
        "just the code",
    ]
    return any(t in p for t in triggers)


def clean_llm_response(raw_text: str, is_code_only: bool = False) -> str:
    """
    Strips internal thinking/reasoning traces (<think>...</think>) and extracts
    strictly the code block if code-only was requested.
    """
    if not raw_text:
        return ""

    text = raw_text.strip()

    # 1. Strip explicit <think>...</think> tags if emitted by reasoning models
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.DOTALL).strip()

    # 2. Strip thinking process headers
    text = re.sub(r"^(Thinking Process:|Reasoning:|Plan:)\s*[\s\S]*?\n(?=```)", "", text, flags=re.IGNORECASE | re.DOTALL).strip()

    # 3. If code only was requested, extract strictly the code block
    if is_code_only:
        code_blocks = re.findall(r"```(?:[a-zA-Z0-9_-]*\n)?([\s\S]*?)```", text)
        if code_blocks:
            # Return strictly markdown code block
            return f"```python\n{code_blocks[0].strip()}\n```"
        else:
            # Fallback: find lines starting from code indicators (import, def, etc.)
            lines = text.splitlines()
            code_lines = []
            capturing = False
            for line in lines:
                if any(line.strip().startswith(kw) for kw in ("import ", "from ", "def ", "class ", "#!/", "#", "if __name__")):
                    capturing = True
                if capturing:
                    code_lines.append(line)
            if code_lines:
                return "```python\n" + "\n".join(code_lines).strip() + "\n```"

    return text


def get_ai_config() -> Tuple[str, Optional[str], str]:
    """
    Returns (base_url, api_key, model_name).
    Checks environment variables and saved configuration.
    Defaults to Kilo Gateway with free model kilo-auto/free (NO API KEY REQUIRED).
    """
    # 1. Kilo AI Gateway (Custom API key if provided)
    kilo_key = os.environ.get("KILO_API_KEY")
    if kilo_key:
        model = os.environ.get("KILO_MODEL") or os.environ.get("AI_MODEL") or DEFAULT_KILO_MODEL
        base_url = os.environ.get("KILO_BASE_URL") or "https://ai-gateway.kilo.ai/api/v1"
        return base_url, kilo_key, model

    # 2. Groq (Blazing fast free tier)
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        model = os.environ.get("GROQ_MODEL") or os.environ.get("AI_MODEL") or DEFAULT_GROQ_MODEL
        return "https://api.groq.com/openai/v1", groq_key, model

    # 3. OpenRouter (Free models)
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if or_key:
        model = os.environ.get("OPENROUTER_MODEL") or os.environ.get("AI_MODEL") or DEFAULT_OPENROUTER_MODEL
        return "https://openrouter.ai/api/v1", or_key, model

    # 4. Google Gemini API
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        model = os.environ.get("GEMINI_MODEL") or os.environ.get("AI_MODEL") or DEFAULT_GEMINI_MODEL
        return "https://generativelanguage.googleapis.com/v1beta/openai", gemini_key, model

    # 5. Generic AI_API_KEY
    generic_key = os.environ.get("AI_API_KEY")
    if generic_key:
        base_url = os.environ.get("AI_BASE_URL", "https://openrouter.ai/api/v1")
        model = os.environ.get("AI_MODEL", DEFAULT_OPENROUTER_MODEL)
        return base_url, generic_key, model

    # 6. DEFAULT ZERO-CONFIG: Kilo AI Gateway free tier (NO API KEY REQUIRED!)
    base_url = os.environ.get("KILO_BASE_URL") or "https://ai-gateway.kilo.ai/api/v1"
    model = os.environ.get("KILO_MODEL") or os.environ.get("AI_MODEL") or DEFAULT_KILO_MODEL
    return base_url, None, model


def query_llm(
    prompt: str,
    history: Optional[List[dict]] = None,
    custom_key: Optional[str] = None,
    custom_model: Optional[str] = None,
    custom_url: Optional[str] = None,
) -> str:
    """
    Sends chat completion request to configured OpenAI-compatible LLM endpoint.
    """
    base_url, api_key, model = get_ai_config()

    if custom_key:
        api_key = custom_key
    if custom_model:
        model = custom_model
    if custom_url:
        base_url = custom_url

    code_only = is_code_only_request(prompt)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if code_only:
        messages.append({
            "role": "system",
            "content": "IMPORTANT: The user has requested ONLY CODE. Output ONLY executable code inside a single ```python ... ``` block. Strictly NO explanation, NO introduction, NO conversational text, and NO thoughts before or after the code block."
        })

    if history:
        for h in history[-6:]:
            role = "user" if h.get("client_type") in ("terminal", "web") else "assistant"
            messages.append({"role": role, "content": h.get("text", "")})

    messages.append({"role": "user", "content": prompt})

    endpoint = f"{base_url.rstrip('/')}/chat/completions"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2 if code_only else 0.5,
        "max_tokens": 4000,
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "termchat-server/1.0",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if "openrouter" in base_url:
        headers["HTTP-Referer"] = "https://github.com/shanmukhasaireddy13/termchat-server"
        headers["X-Title"] = "termchat"

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                raw_content = msg.get("content") or ""

                # If content was empty but reasoning contains code block:
                if not raw_content and msg.get("reasoning"):
                    reasoning_text = msg.get("reasoning", "")
                    code_match = re.search(r"```(?:[a-zA-Z0-9_-]*\n)?([\s\S]*?)```", reasoning_text)
                    if code_match:
                        raw_content = code_match.group(0)

                cleaned = clean_llm_response(raw_content, is_code_only=code_only)
                return cleaned if cleaned else "No response generated by model."
            return "No response generated by model."
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        try:
            err_json = json.loads(err_body)
            msg = err_json.get("error", {}).get("message") or err_body
        except Exception:
            msg = err_body
        return f"[AI Error ({e.code})]: {msg}"
    except Exception as e:
        return (
            f"[AI Error: {e}]\n"
            "TermChat AI connects to Kilo AI Gateway by default. To use custom keys:\n"
            "Set GROQ_API_KEY, KILO_API_KEY, or OPENROUTER_API_KEY in your Render environment variables."
        )

