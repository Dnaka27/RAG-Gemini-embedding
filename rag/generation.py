from .config import GENERATION_MODEL


def generate_answer(client, question, context, temperature=0.7):
    prompt = f"""
Base the answer **only** on the context below:

{context}

Question:
{question}

Answer objectively and clearly.
"""
    resp = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=[prompt],
        config={"temperature": temperature},
    )
    answer = (resp.text or "").strip()
    if not answer:
        raise ValueError("Gemini returned no answer (it may have been blocked or cut off). Try rephrasing the question.")
    return answer
