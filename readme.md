# RAG com Gemini — Banco Vetorial e Consulta

Este projeto implementa RAG simples usando Google Gemini para geração e embeddings, FAISS para busca vetorial e um arquivo Markdown como base para respostas contextuais.

## Funcionalidades
- Leitura de um arquivo `.md`
- Chunking dinâmico com overlap
- Geração de embeddings (gemini-embedding-001)
- Criação de banco FAISS
- Consulta vetorial e resposta contextualizada

## Estrutura do Projeto
```
project/
├── reference.md
├── storage/
│   ├── vector_db.index
│   └── schema_chunks.json
└── notebook.ipynb
```

## Instalação
Crie um ambiente virtual:
```
python -m venv .venv
```
Ative:
- Windows: `.venv\Scripts\activate`
- Linux/Mac: `source .venv/bin/activate`

Instale as dependências:
```
pip install -r requirements.txt
```

## Variáveis de Ambiente

Para executar o projeto, é necessário criar uma chave de API do Google Gemini.
A chave pode ser gerada acessando o site oficial do Google AI Studio:
https://aistudio.google.com/

Crie um arquivo `.env` com:
```
GEMINI_API_KEY=sua_chave
```

## Uso
Coloque `reference.md` na raiz e execute o notebook

Ele irá:
1. Ler o arquivo
2. Realizar chunking
3. Gerar embeddings
4. Criar o banco FAISS
5. Permitir consultas via input

## Funcionamento do RAG
O pipeline aplica chunking, gera embeddings dos trechos, salva o banco FAISS, cria embeddings da pergunta, recupera os trechos mais próximos e envia um prompt ao Gemini contendo contexto + pergunta.

## Requisitos principais
- google-genai
- faiss-cpu
- numpy
- python-dotenv
- tqdm
- ipython