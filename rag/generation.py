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
    return resp.candidates[0].content.parts[0].text
