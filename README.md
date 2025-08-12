# **MAGI – Research Agent (v1.5)**

Deep research agent using LLMs and web search, designed to answer questions with updated, structured, and automatically reviewed information.

---

## **1. General Functionality**
MAGI receives a user question, generates optimized search queries, searches multiple sources using the Tavily API, summarizes the results, compiles a final answer with references, and performs a review to check coherence and accuracy.

Execution flow:
1. **User input** → Question to be researched.
2. **Query generation** (`build_first_queries`).
3. **Parallel web searches** for each query (`single_search`).
4. **Final answer compilation** with references (`final_writer`).
5. **Review and validation** using another LLM (`reviewer`).
6. **Display of the final report** in Streamlit.

---

## **2. File Structure**
- **`magi.py`** – Main agent logic, execution graph definition, integration with LLMs, Tavily, and Streamlit.
- **`prompts.py`** – Prompt templates used in the different flow stages (query generation, summarization, final answer, review).
- **`schemas.py`** – Data structures (Pydantic) for typing and state sharing in the graph.
- **`requirments.txt`** – List of dependencies required to run the project.

---

## **3. Dependencies**
From `requirments.txt`:
```
streamlit
langgraph
langchain
python-dotenv
langchain-ollama
tavily-python
```
Additional requirements:
- **Python 3.10+** recommended.
- **Ollama models** (`llama3.1:8b-instruct-q4_K_S` and `deepseek-r1:8b`) must be available locally or via the Ollama API.
- **Tavily API key** configured in `.env`.

---

## **4. Installation**
1. Clone or copy the project to your environment.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate   # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirments.txt
   ```
4. Create a `.env` file in the project root:
   ```
   TAVILY_API_KEY=your_tavily_api_key
   ```
5. Ensure Ollama is running and models are installed:
   ```bash
   ollama pull llama3.1:8b-instruct-q4_K_S
   ollama pull deepseek-r1:8b
   ```

---

## **5. Execution**
To start the interface:
```bash
streamlit run magi.py
```
Open the link shown in the terminal (usually `http://localhost:8501`).

---

## **6. How to Use**
1. In the Streamlit text field, type your research question.  
   Example: *"What are the latest advancements in AI for drug discovery?"*
2. Click **"Research"**.
3. Monitor the progress bar and status updates in real time.
4. At the end:
   - Expand **"✅ Generated Queries"** to view the generated search queries.
   - Read the reviewed final report in the **Final Research Report** section.

---

## **7. Internal Operation**
- **LLM Models**:
  - `llama3.1:8b-instruct-q4_K_S`: general tasks (generate queries, summarize content).
  - `deepseek-r1:8b`: reasoning and review tasks.
- **Web Search**: `TavilyClient` performs search and content extraction.
- **Graph Structure** (`langgraph`): each step is a node connected for ordered execution.
- **Custom Prompts**: ensure format, accuracy, and response style.
- **References**: each paragraph in the final answer includes numbered citations linked to sources.

---

## **8. Important Notes**
- **Answer quality** depends on Tavily search coverage.
- **Token limits**: very long queries or content may exceed model context limits.
- **Review format**: if the reviewer finds issues, it will output a corrected version inside `<CORRECTED_FINAL_RESPONSE>`.

---

## **9. Example Usage**
Question:  
*"Impacts of quantum computing on cryptography in 2025"*

Expected flow:
1. Generate 3–8 targeted queries.
2. Search and summarize each result.
3. Build a final text of 500–800 words with citations.
4. Review for accuracy and consistency.

---

## **10. Possible Extensions**
- Change Ollama models to larger or alternative versions.
- Integrate additional search providers beyond Tavily.
- Adjust search (`max_results`) and synthesis parameters for higher precision.

---
