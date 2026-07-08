from .config import GENERATION_MODEL


def generate_answer(client, question, context, temperature=0.7):
    prompt = f"""
Baseie a resposta **somente** no contexto abaixo:

{context}

Pergunta:
{question}

Responda de forma objetiva e clara.
"""
    resp = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=[prompt],
        config={"temperature": temperature},
    )
    return resp.candidates[0].content.parts[0].text
