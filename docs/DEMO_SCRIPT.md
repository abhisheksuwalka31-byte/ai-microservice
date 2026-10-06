# 🎬 2-Minute Demo Script & Video Recording Guide

This guide provides the exact script and step-by-step actions to record your 2-minute Loom demo for the **AI Microservice**.

---

## 📋 Pre-Recording Setup

1. **Start the server locally**:
   ```bash
   cd /Users/abhisuwalka/.gemini/antigravity/scratch/ai-microservice
   source venv/bin/activate
   python run.py
   ```
2. **Open your browser**:
   - Tab 1: `http://127.0.0.1:8000/docs` (Swagger UI)
   - Tab 2: Terminal or Postman showing execution logs / tests
3. **Open Loom** (Screen + Mic recording)

---

## ⏱️ Timeline & Narration

### [0:00 - 0:25] Introduction & Architecture Overview
* **Action**: Show Swagger UI at `http://127.0.0.1:8000/docs` and code editor.
* **Narration**:
  > *"Hello! Today I'm showcasing our containerized AI Microservice built with FastAPI, Pydantic v2, and the Google Gemini API. It provides a modular backend supporting text generation, multi-turn chat, text summarization, and multimodal image understanding—fully secured with JWT authentication and packaged with Docker for seamless local and production deployments."*

### [0:25 - 0:50] Authentication & Security
* **Action**: Expand `POST /api/v1/auth/register` or `POST /api/v1/auth/token`. Register a user, copy the token, and click **Authorize** at the top right of Swagger UI to paste the Bearer token.
* **Narration**:
  > *"Security is enforced at every AI endpoint. First, clients register or log in to obtain a cryptographically signed JWT access token. Notice that attempting to call any AI endpoint without a valid token immediately triggers an HTTP 401 Unauthorized error. Once authorized with our token, all microservice capabilities unlock."*

### [0:50 - 1:20] Core Inference: Text Generation & Multi-turn Chat
* **Action**:
  1. Open `POST /api/v1/ai/generate`, run a prompt like *"Explain microservices architecture in 2 bullet points."*
  2. Open `POST /api/v1/ai/chat`, run a conversation with alternating `user` and `model` roles.
* **Narration**:
  > *"Our text generation endpoint allows customizable system instructions, sampling temperature, and token limits. For interactive assistants, the multi-turn chat endpoint validates message histories using strict Pydantic v2 schemas and keeps contextual conversation threads fluent."*

### [1:20 - 1:45] Text Summarization & Multimodal Image Understanding
* **Action**:
  1. Open `POST /api/v1/ai/summarize` with `style="bullet"`.
  2. Open `POST /api/v1/ai/analyze-image`, attach a sample image, and execute.
* **Narration**:
  > *"We also provide a dedicated summarization endpoint supporting concise, detailed, and bullet styles. Furthermore, our multimodal endpoint allows users to upload images—such as charts, diagrams, or photos—and prompts Gemini Vision to extract insights, perform OCR, or describe the content in detail."*

### [1:45 - 2:00] Containerization, Testing & Conclusion
* **Action**: Switch to Terminal, show `docker-compose.yml` and run `pytest -v` passing tests.
* **Narration**:
  > *"The service includes automated health checks, a comprehensive pytest test suite covering authentication guards and validation, and is fully containerized using Docker and Docker Compose for single-command startup. Thank you!"*

---

## 💡 Quick Tips for Recording
- Keep the Swagger UI zoomed in slightly (110%-125%) for clear legibility on video.
- Have a pre-registered username/password ready or test with the `/api/v1/auth/register` endpoint in Swagger.
- Total time should be roughly 1:50 - 2:10 minutes.
