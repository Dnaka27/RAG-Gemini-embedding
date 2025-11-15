# Conversa com PDFs usando RAG + Gemini

Este projeto implementa **RAG (Retrieval-Augmented Generation)** com **Google Gemini** de forma simples para permitir que você faça perguntas sobre o conteúdo de um PDF e obtenha respostas contextuais em linguagem natural.

## 🚀 Funcionalidades
- Extração de texto de documentos PDF.
- Divisão do texto em chunks otimizados para embeddings.
- Criação de base vetorial local usando **ChromaDB**.
- Geração de embeddings com **Google Generative AI**.
- Uso do modelo **Gemini 2.5 Flash** para responder perguntas.
- Interface simples em linha de comando para interação.

---

## 🛠️ Tecnologias Utilizadas
- [Python](https://www.python.org/)  
- [LangChain](https://www.langchain.com/)  
- [Chroma](https://www.trychroma.com/)  
- [Google Generative AI](https://ai.google.dev/)  
- [dotenv](https://pypi.org/project/python-dotenv/)  

---

## 📂 Estrutura do Projeto
```
.
├── main.py                # Script principal
├── sample_apostila.pdf    # Exemplo de PDF para testes
├── chroma_db/             # Base vetorial persistida
├── .env                   # Contém a variável GEMINI_API_KEY
└── README.md
```

---

## ⚙️ Configuração

### 1. Clone o repositório
```bash
git clone https://github.com/seu-usuario/meu-projeto.git
cd meu-projeto
```

### 2. Crie um ambiente virtual
```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure sua chave da API Gemini
Crie um arquivo `.env` na raiz do projeto:
```
GEMINI_API_KEY=coloque_sua_chave_aqui
```

---

## ▶️ Uso
Coloque o PDF que deseja consultar na pasta do projeto e ajuste o caminho em `pdf_path` no código.

Execute o script:
```bash
python main.py
```

Você verá:
```
Pronto para conversar com seu PDF. Digite 'sair' para encerrar.
Sua pergunta:
```

Agora, basta fazer perguntas em português sobre o PDF.

---

## 📜 Licença
Este projeto é open-source sob a licença MIT.
