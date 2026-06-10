#!/usr/bin/env python3
import os
import json
import sys
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from openai import OpenAI

# Reuse configuration logic
ROOT = Path(__file__).parent
PROMPT_PATH = ROOT / "agent" / "interview_qa.md"
ROUTERS_FILE = ROOT / os.getenv("ROUTERS_FILE", "routers.json")

app = Flask(__name__)
CORS(app)

def load_prompt() -> str:
    return PROMPT_PATH.read_text() if PROMPT_PATH.exists() else ""

def load_routers():
    strategy = os.getenv("ROUTER_STRATEGY", "round_robin")
    routers = [os.getenv("BASE_URL", "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1")]
    if ROUTERS_FILE.exists():
        data = json.loads(ROUTERS_FILE.read_text())
        routers = data.get("routers", routers) or routers
        strategy = data.get("strategy", strategy)
    return routers, strategy

def get_client(base_url: str) -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "dummy")
    return OpenAI(api_key=api_key, base_url=base_url)

def build_messages(topic: str, question: str, context: str, audience: str, prompt: str):
    user_payload = {
        "topic": topic,
        "question": question,
        "context": context,
        "audience": audience,
    }
    return [
        {"role": "system", "content": prompt or "You are an interview Q&A agent."},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]

# Serve single-page Frontend directly via template rendering
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interview Q&A Agent Dashboard</title>
    <!-- Modern Outfits font & Tailwind CSS via CDN for rapid clean layouts -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <!-- Marked JS for Markdown rendering -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 29, 49, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 2rem 1rem;
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(168, 85, 247, 0.15) 0px, transparent 50%);
            background-attachment: fixed;
        }

        .container {
            width: 100%;
            max-width: 900px;
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }

        header {
            text-align: center;
            margin-bottom: 1rem;
        }

        header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(to right, #818cf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }

        header p {
            color: var(--text-muted);
            font-size: 1.1rem;
        }

        .card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }

        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }

        @media (max-width: 768px) {
            .form-grid {
                grid-template-columns: 1fr;
            }
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .form-group.full-width {
            grid-column: span 2;
        }

        @media (max-width: 768px) {
            .form-group.full-width {
                grid-column: span 1;
            }
        }

        label {
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        input, textarea {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 0.8rem 1rem;
            color: var(--text-main);
            font-size: 1rem;
            transition: all 0.3s ease;
            outline: none;
        }

        input:focus, textarea:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
        }

        button {
            background: var(--primary);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 1rem;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }

        button:hover {
            background: var(--primary-hover);
            transform: translateY(-2px);
        }

        button:disabled {
            background: var(--text-muted);
            cursor: not-allowed;
            transform: none;
        }

        /* Response Box Styles */
        .response-container {
            display: none;
            flex-direction: column;
            gap: 1rem;
        }

        .response-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.75rem;
        }

        .router-badge {
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
            padding: 0.25rem 0.75rem;
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 600;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .output-content {
            line-height: 1.7;
            font-size: 1.05rem;
        }

        .output-content h1, .output-content h2, .output-content h3 {
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            font-weight: 600;
            color: #818cf8;
        }

        .output-content p {
            margin-bottom: 1rem;
        }

        .output-content ul, .output-content ol {
            margin-left: 1.5rem;
            margin-bottom: 1rem;
        }

        .output-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
        }

        .output-content th, .output-content td {
            border: 1px solid var(--border-color);
            padding: 0.75rem;
            text-align: left;
        }

        .output-content th {
            background: rgba(99, 102, 241, 0.1);
            color: #a5b4fc;
        }

        /* Loading Spinner */
        .spinner {
            border: 3px solid rgba(255, 255, 255, 0.1);
            width: 24px;
            height: 24px;
            border-radius: 50%;
            border-left-color: white;
            animation: spin 1s linear infinite;
            display: none;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .error-message {
            color: #ef4444;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: 8px;
            padding: 1rem;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Interview Q&A Agent</h1>
            <p>Powered by VNG Cloud MaaS & Minimax-m2.5</p>
        </header>

        <main class="card">
            <form id="qaForm" class="form-grid">
                <div class="form-group">
                    <label for="topic">Topic</label>
                    <input type="text" id="topic" value="ZaloPay SB testing" required>
                </div>
                <div class="form-group">
                    <label for="model">Model</label>
                    <input type="text" id="model" value="minimax/minimax-m2.5" required>
                </div>
                <div class="form-group full-width">
                    <label for="question">Question</label>
                    <textarea id="question" rows="3" required>How would you test the loan repayment create API?</textarea>
                </div>
                <div class="form-group">
                    <label for="context">Context (Optional)</label>
                    <input type="text" id="context" placeholder="e.g. Senior QA Engineer Interview">
                </div>
                <div class="form-group">
                    <label for="audience">Audience (Optional)</label>
                    <input type="text" id="audience" placeholder="e.g. Technical Interviewer">
                </div>

                <button type="submit" id="submitBtn" class="full-width">
                    <span id="btnText">Generate Response</span>
                    <div class="spinner" id="btnSpinner"></div>
                </button>
            </form>
        </main>

        <section class="card response-container" id="responseCard">
            <div class="response-header">
                <h2 style="font-size: 1.3rem; font-weight: 600;">Response</h2>
                <span class="router-badge" id="routerBadge">Router: None</span>
            </div>
            <div id="output" class="output-content"></div>
        </section>

        <div class="error-message" id="errorMessage"></div>
    </div>

    <script>
        document.getElementById('qaForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = document.getElementById('submitBtn');
            const btnText = document.getElementById('btnText');
            const btnSpinner = document.getElementById('btnSpinner');
            const responseCard = document.getElementById('responseCard');
            const output = document.getElementById('output');
            const routerBadge = document.getElementById('routerBadge');
            const errorMessage = document.getElementById('errorMessage');

            // Reset states
            errorMessage.style.display = 'none';
            responseCard.style.display = 'none';
            submitBtn.disabled = true;
            btnText.style.display = 'none';
            btnSpinner.style.display = 'block';

            const payload = {
                topic: document.getElementById('topic').value,
                model: document.getElementById('model').value,
                question: document.getElementById('question').value,
                context: document.getElementById('context').value,
                audience: document.getElementById('audience').value
            };

            try {
                const response = await fetch('/api/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'Server returned an error');
                }

                routerBadge.innerText = `Router: ${data.router}`;
                output.innerHTML = marked.parse(data.answer);
                responseCard.style.display = 'flex';
            } catch (err) {
                errorMessage.innerText = err.message;
                errorMessage.style.display = 'block';
            } finally {
                submitBtn.disabled = false;
                btnText.style.display = 'block';
                btnSpinner.style.display = 'none';
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(INDEX_HTML)

@app.route('/health')
def health():
    return "OK", 200

@app.route('/api/ask', methods=['POST'])
def api_ask():
    data = request.json or {}
    topic = data.get('topic', '')
    question = data.get('question', '')
    context = data.get('context', '')
    audience = data.get('audience', '')
    model = data.get('model', 'minimax/minimax-m2.5')

    if not topic or not question:
        return jsonify({"error": "Topic and Question are required"}), 400

    routers, strategy = load_routers()
    prompt = load_prompt()
    messages = build_messages(topic, question, context, audience, prompt)
    last_error = None

    for base_url in routers:
        try:
            client = get_client(base_url)
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.2,
            )
            content = resp.choices[0].message.content or ""
            return jsonify({
                "answer": content,
                "router": base_url
            })
        except Exception as e:
            last_error = str(e)
            continue

    return jsonify({"error": f"All routers failed: {last_error}"}), 500

if __name__ == '__main__':
    port = int(os.getenv("PORT", 8080))
    # Run on all network interfaces to allow external access if desired
    app.run(host='0.0.0.0', port=port, debug=True)
