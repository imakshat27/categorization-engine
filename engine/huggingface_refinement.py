import os

import requests

from engine.ai_refinement import refine_transactions


HUGGINGFACE_MODEL_OPTIONS = [
    "meta-llama/Llama-3.1-8B-Instruct:preferred",
    "meta-llama/Llama-3.1-8B-Instruct:cheapest",
    "openai/gpt-oss-20b:groq",
    "zai-org/GLM-5:fireworks-ai",
    "zai-org/GLM-5:together",
    "deepseek-ai/DeepSeek-R1:hyperbolic",
    "katanemo/Arch-Router-1.5B:hf-inference",
]
DEFAULT_HUGGINGFACE_MODEL = HUGGINGFACE_MODEL_OPTIONS[0]
DEFAULT_HUGGINGFACE_BASE_URL = "https://router.huggingface.co/v1/chat/completions"
DEFAULT_HUGGINGFACE_LOG_PATH = "output/huggingface_refinement_logs.jsonl"


def _token(explicit_token=None):
    return (
        explicit_token
        or os.getenv("HF_TOKEN")
        or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    )


def _message_content(content):
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))

        return "\n".join(part for part in parts if part)

    return ""


def call_huggingface_chat(
    prompt,
    model=DEFAULT_HUGGINGFACE_MODEL,
    token=None,
    base_url=DEFAULT_HUGGINGFACE_BASE_URL,
    timeout=120,
    request_json_response=False,
):
    auth_token = _token(token)

    if not auth_token:
        raise ValueError(
            "Set HF_TOKEN, HUGGINGFACEHUB_API_TOKEN, or paste a token in the Streamlit field."
        )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Validate deterministic transaction categorization. Return JSON only.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0,
        "top_p": 0.1,
        "max_tokens": 512,
        "stream": False,
    }

    if request_json_response:
        payload["response_format"] = {
            "type": "json_object",
        }

    response = requests.post(
        base_url,
        headers={
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )

    if response.status_code >= 400:
        raise ValueError(
            f"Hugging Face HTTP {response.status_code}: {response.text[:1200]}"
        )

    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Unexpected Hugging Face response: {data}") from exc

    return _message_content(content)


def refine_transactions_with_huggingface(
    processed_df,
    threshold,
    model=DEFAULT_HUGGINGFACE_MODEL,
    token=None,
    base_url=DEFAULT_HUGGINGFACE_BASE_URL,
    log_path=DEFAULT_HUGGINGFACE_LOG_PATH,
    include_old_category_disagreement=False,
    max_rows=None,
    request_json_response=False,
    routing_policy="balanced",
    log_skipped="summary",
    log_detail="summary",
):
    def generate(prompt):
        return call_huggingface_chat(
            prompt,
            model=model,
            token=token,
            base_url=base_url,
            request_json_response=request_json_response,
        )

    return refine_transactions(
        processed_df,
        threshold=threshold,
        model=model,
        base_url=base_url,
        generate_func=generate,
        log_path=log_path,
        include_old_category_disagreement=include_old_category_disagreement,
        max_rows=max_rows,
        provider="huggingface",
        routing_policy=routing_policy,
        log_skipped=log_skipped,
        log_detail=log_detail,
    )
