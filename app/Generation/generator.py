from openai import OpenAI
from app.core.prompts import SYSTEM_PROMPT
from app.core.prompt_firewall import sanitize_context
from app.observability.cost import record_cost
from app.core.tenant import get_tenant

client = OpenAI()

def generate_answer(query, context_docs):
    """
    Enterprise-grade generation with:
    - prompt-injection defense
    - deterministic output
    - tenant-aware cost tracking
    """

    tenant = get_tenant() or "default"

    # 🔒 Sanitize retrieved context
    safe_context_blocks = []
    for doc in context_docs:
        clean_text = sanitize_context(doc.page_content)
        safe_context_blocks.append(clean_text)

    context = "\n\n".join(
        f"[DOC {i}] {text}"
        for i, text in enumerate(safe_context_blocks)
    )

    user_prompt = f"""
Context (trusted, sanitized):
{context}

Question:
{query}

Rules:
- Answer ONLY using the context above
- If insufficient information exists, say so
- Cite documents using [DOC X]
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0,
        max_tokens=600
    )

    answer = response.choices[0].message.content

    # 💰 TOKEN + COST CAPTURE (THIS IS WHAT YOU ASKED ABOUT)
    usage = response.usage

    record_cost(
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        model="gpt-4o",
        query=query
    )

    return answer
