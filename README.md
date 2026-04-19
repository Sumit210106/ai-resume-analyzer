# ResumeAI Pro | AI-Powered Resume Analyst

**ResumeAI Pro** is a high-performance, RAG-powered (Retrieval-Augmented Generation) resume analysis engine designed to provide deep strategic fit insights between candidates and job descriptions.

Built with **Streamlit**, **Llama 3.3 (via Groq)**, and **FAISS**, it offers a professional, SaaS-grade interface for recruiters and candidates to evaluate alignment probability with extreme precision.

## 🚀 Features

- **Deep Contextual Mapping**: Uses FAISS vector indexing to intelligently retrieve relevant resume fragments.
- **Vercel-Inspired UI**: Minimalist, high-contrast professional interface with a stage-based workflow.
- **Match Probability Gauge**: High-fidelity SVG visualization of candidate alignment.
- **Skill Inventory Synthesis**: Automated extraction and tagging of matching vs missing capabilities.
- **Strategic Action Roadmap**: Detailed, LLM-generated suggestions for resume optimization.
- **Privacy First**: Data is processed locally and via secure, ephemeral API calls.

## 🛠️ Tech Stack

- **UI Framework**: Streamlit
- **LLM Engine**: Groq (Llama 3.3 70B)
- **Vector Store**: FAISS
- **Embeddings**: HuggingFace (sentence-transformers)
- **Orchestration**: LangChain

## 📦 Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd ai-resume-analyzer
   ```

2. **Initialize Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Mac/Linux
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_api_key_here
   ```

4. **Launch Application**:
   ```bash
   streamlit run app.py
   ```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---
*Built with ❤️ for the modern hiring ecosystem.*
