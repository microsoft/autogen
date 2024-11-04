'''
from flask import Flask, render_template_string, jsonify, request, send_file
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any
import os
import re
import markdown
from pathlib import Path
import threading
import time

app = Flask(__name__)

# Global variable to store logs and log directory
LOGS: List[Dict[str, Any]] = []
LOG_DIR: str = ""

# Add markdown extension for fenced code blocks
md = markdown.Markdown(extensions=["fenced_code", "tables"])

# HTML template with embedded CSS and JavaScript
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Log Viewer</title>
    <!-- Add highlight.js for code syntax highlighting -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 70vw;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            height: 80vh;
            overflow-y: auto;
        }
        
        .message {
            margin-bottom: 20px;
            max-width: 80%;
            animation: fadeIn 0.5s ease-in;
        }
        
        .message.user {
            margin-left: auto;
        }
        
        .message-content {
            padding: 12px;
            border-radius: 8px;
            overflow-wrap: break-word;
        }
        
        .user .message-content {
            background-color: #f3f4f6;
            color: black;
        }
        
        .user .message-content pre {
            background-color: rgba(255, 255, 255, 0.1) !important;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .orchestrator .message-content {
            background-color: #f3e8ff;
            border: 1px solid #e9d5ff;
        }
        
        .websurfer .message-content {
            background-color: #f3f4f6;
            border: 1px solid #e5e7eb;
        }
        
        .system .message-content {
            background-color: #f3f4f6;
            border: 1px solid #e5e7eb;
        }
        
        .message-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }
        
        .source {
            font-weight: 600;
            font-size: 0.9em;
        }
        
        .timestamp {
            color: #666;
            font-size: 0.8em;
        }
        
        pre {
            background-color: #f8f9fa !important;
            padding: 12px !important;
            border-radius: 6px !important;
            overflow-x: auto !important;
            margin: 8px 0 !important;
            font-size: 0.9em !important;
        }
        
        code {
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace !important;
        }
        
        .screenshot {
            margin-top: 12px;
        }
        
        .screenshot img {
            max-width: 50%;
            border-radius: 6px;
            border: 1px solid #e5e7eb;
        }
        
        .token-info {
            margin-top: 8px;
            font-size: 0.8em;
            color: #666;
        }

        .controls {
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            gap: 10px;
        }

        button {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            background-color: #007bff;
            color: white;
            cursor: pointer;
        }

        button:hover {
            background-color: #0056b3;
        }

        button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        
        /* Markdown content styling */
        .markdown-content h1,
        .markdown-content h2,
        .markdown-content h3,
        .markdown-content h4,
        .markdown-content h5,
        .markdown-content h6 {
            margin-top: 1em;
            margin-bottom: 0.5em;
        }
        
        .markdown-content p {
            margin: 0.5em 0;
        }
        
        .markdown-content ul,
        .markdown-content ol {
            margin: 0.5em 0;
            padding-left: 1.5em;
        }
        
        .markdown-content table {
            border-collapse: collapse;
            margin: 1em 0;
            width: 100%;
        }
        
        .markdown-content th,
        .markdown-content td {
            border: 1px solid #e5e7eb;
            padding: 8px;
            text-align: left;
        }
        
        .markdown-content th {
            background-color: #f8f9fa;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
 /* Ledger specific styling */
        .ledger-item {
            margin: 10px 0;
            padding: 8px;
            border-left: 3px solid #e9d5ff;
        }

        .ledger-title {
            font-weight: 600;
            margin-bottom: 4px;
        }

        .ledger-reason {
            font-size: 0.9em;
            color: #666;
            margin-left: 20px;
            font-style: italic;
        }

        .ledger-checkbox {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #666;
            border-radius: 3px;
            margin-right: 8px;
            position: relative;
            top: 2px;
        }

        .ledger-checkbox.checked::after {
            content: "✓";
            position: absolute;
            color: #4CAF50;
            font-weight: bold;
            left: 1px;
            top: -2px;
        }
    </style>
</head>
<body>
    <div class="controls">
        <button id="pauseBtn">Pause</button>
        <button id="resetBtn">Reset</button>
    </div>
    <div class="container" id="messages"></div>

    <script>
        let isPaused = false; // Ensure this is set to false initially
        let currentIndex = 0;

        document.getElementById('pauseBtn').addEventListener('click', function() {
            isPaused = !isPaused;
            this.textContent = isPaused ? 'Resume' : 'Pause';
            if (!isPaused) {
                addNextMessage();
            }
        });

        document.getElementById('resetBtn').addEventListener('click', function() {
            currentIndex = 0;
            document.getElementById('messages').innerHTML = '';
            if (isPaused) {
                isPaused = false;
                document.getElementById('pauseBtn').textContent = 'Pause';
                addNextMessage();
            }
        });

        function formatLedger(ledgerData) {
            try {
                const ledger = JSON.parse(ledgerData);
                let html = '<div class="ledger-container">';
                
                for (const [key, value] of Object.entries(ledger)) {
                    html += `
                        <div class="ledger-item">
                            <div class="ledger-title">
                                ${key === 'is_request_satisfied' ? 'Request Satisfied' :
                                  key === 'is_in_loop' ? 'In Loop' :
                                  key === 'is_progress_being_made' ? 'Progress Being Made' :
                                  key === 'next_speaker' ? 'Next Speaker' :
                                  key === 'instruction_or_question' ? 'Instruction/Question' :
                                  key}:
                                ${typeof value.answer === 'boolean' ? 
                                  `<span class="ledger-checkbox ${value.answer ? 'checked' : ''}"></span>` :
                                  `<strong>${value.answer}</strong>`}
                            </div>
                            <div class="ledger-reason">
                                ${value.reason}
                            </div>
                        </div>`;
                }
                
                html += '</div>';
                return html;
            } catch (e) {
                console.error('Error parsing ledger:', e);
                return ledgerData;
            }
        }

        function createMessageElement(log) {
            const messageDiv = document.createElement('div');
            const source = log.source || 'System';
            if (source === 'System') {
            // dont create message element for system logs
                return;
            }

            messageDiv.className = `message ${source.toLowerCase().includes('orchestrator') ? 'orchestrator' : 
                                          source === 'UserProxy' ? 'user' : 
                                          source === 'WebSurfer' ? 'websurfer' : 'system'}`;

            const iconMap = {
                'UserProxy': 'user_proxy.png',
                'Orchestrator': 'orchestrator.png',
                'WebSurfer': 'websurfer.png',
                'Coder': 'coder.png',
                'Executor': 'computerterminal.png',
                'file_surfer': 'filesurfer.png'
            };

            const iconSrc = iconMap[source] ? `/icons/${iconMap[source]}` : '';

            let messageHtml = `
                <div class="message-content">
                    <div class="message-header">
                        ${iconSrc ? `<img src="${iconSrc}" alt="${source} icon" style="width: 24px; height: 24px;">` : ''}
                        <span class="source">${source}</span>
                    </div>
                    `;
            let messageContent = log.message;

            if (source.toLowerCase().includes('orchestrator') && messageContent.includes('Updated Ledger:')) {
                const ledgerStart = messageContent.indexOf('{');
                const ledgerEnd = messageContent.lastIndexOf('}') + 1;
                const ledgerJson = messageContent.substring(ledgerStart, ledgerEnd);
                messageContent = formatLedger(ledgerJson);
                messageHtml += `
                    <div class="markdown-content">${messageContent}</div>`;
            }
            // check if message includes "Here is a screenshot of", if so remove everyting after that including it
            else if (messageContent.includes('Here is a screenshot of')) {
                messageContent = messageContent.split('Here is a screenshot of')[0];
                messageHtml += `
                    <div class="markdown-content">${messageContent}</div>`;
            }
            else {
                messageHtml += `
                    <div class="markdown-content">${log.message_html || log.message}</div>`;
            }
            // Handle screenshots for WebSurfer messages
            if (log.message && log.message.startsWith('Screenshot:')) {
                const screenshotFile = log.message.split(': ')[1];
                // check if _som is in the screenshot file name
                if (screenshotFile.includes('_som')) {
                    return;
                }
                
                messageHtml = `
                    <div class="message-content">
                        <div class="message-header">
                            ${iconSrc ? `<img src="${iconSrc}" alt="${source} icon" style="width: 24px; height: 24px;">` : ''}
                            <span class="source">${source}</span>
                        </div>
                    <div class="screenshot">
                        <img src="/screenshots/${screenshotFile}" alt="Screenshot">
                    </div>`;
            }

            // Add token info for LLM calls
            if (log.type === 'LLMCallEvent') {
                messageHtml += `
                    <div class="token-info">
                        Tokens: ${log.prompt_tokens} prompt, ${log.completion_tokens} completion
                    </div>`;
            }

            messageHtml += '</div>';
            messageDiv.innerHTML = messageHtml;

            // Apply syntax highlighting to code blocks
            messageDiv.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });

            return messageDiv;
        }

        function addNextMessage() {
            if (isPaused) return;
            
            fetch(`/logs?index=${currentIndex}`)
                .then(response => response.json())
                .then(data => {
                    if (data.log) {
                        const messageElement = createMessageElement(data.log);
                        if (!messageElement) {
                            currentIndex++;
                            setTimeout(addNextMessage, 500);
                            return;
                        }
                        const container = document.getElementById('messages');
                        container.appendChild(messageElement);
                        // container.scrollTop = container.scrollHeight;
                        messageElement.scrollIntoView({ behavior: 'smooth', block: 'start' });

                        currentIndex++;
                        setTimeout(addNextMessage, 1500);
                    }
                });
        }

        // Start displaying logs when page loads
        document.addEventListener('DOMContentLoaded', function() {
            addNextMessage(); // Ensure this is called on page load
        });
    </script>
</body>
</html>
"""


@app.route("/")
def index() -> str:
    return render_template_string(HTML_TEMPLATE)


@app.route("/logs")
def get_logs() -> jsonify:
    index = int(request.args.get("index", 0))
    if index < len(LOGS):
        log = LOGS[index].copy()
        # Convert message to Markdown HTML if it's a string
        if isinstance(log.get("message"), str):
            log["message_html"] = md.convert(log["message"])
        return jsonify({"log": log})
    return jsonify({"log": None})


@app.route("/screenshots/<path:filename>")
def serve_screenshot(filename: str) -> send_file:
    """Serve screenshot images from the log directory."""
    return send_file(os.path.join(LOG_DIR, filename))


@app.route("/icons/<path:filename>")
def serve_icon(filename: str) -> send_file:
    """Serve icon images from the icons directory."""
    return send_file(os.path.join("magentic_one_icons", filename))


def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """Load logs from a JSONL file."""
    logs = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                logs.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                print(f"Warning: Skipping invalid JSON line: {line.strip()}")

    # process logs
    indices_to_remove = []

    for i, log in enumerate(logs):
        if "source" not in log or "message" not in log:
            indices_to_remove.append(i)
        elif "Orchestrator (thought)" in log["source"] and ("Request satisfied." in log["message"]):
            indices_to_remove.append(i)
        elif "Next speaker" in log["message"] or "No agent selected." in log["message"]:
            indices_to_remove.append(i)
        elif "Orchestrator (->" in log["source"]:
            indices_to_remove.append(i)
        elif "Orchestrator (termination condition)" in log["source"] or "No agent selected." in log["message"]:
            indices_to_remove.append(i)
        elif "type" in log and "WebSurferEvent" in log["type"]:
            # websurfer filtering
            if "New tab or window." in log["message"]:
                indices_to_remove.append(i)
            elif "Screenshot:" not in log["message"]:
                for j in range(i + 1, len(logs)):
                    if (
                        logs[j]["type"] == "OrchestrationEvent"
                        and "source" in logs[j]
                        and logs[j]["source"] == "WebSurfer"
                    ):
                        first_line_log_j = logs[j]["message"].split("\n")[0]
                        logs[i]["message"] += "\n\n" + first_line_log_j
                        break

    for i, log in enumerate(logs):
        if log["type"] == "OrchestrationEvent" and "source" in log and log["source"] == "WebSurfer":
            indices_to_remove.append(i)
    for i, log in enumerate(logs):
        if "source" in log and "Orchestrator" in log["source"]:
            logs[i]["source"] = "Orchestrator"
    logs = [log for i, log in enumerate(logs) if i not in indices_to_remove]

    return logs


def load_logs_from_folder(folder_path: str) -> List[Dict[str, Any]]:
    """Load logs from all JSONL files in the specified folder."""
    logs = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith("log.jsonl"):
            file_path = os.path.join(folder_path, file_name)
            logs.extend(load_jsonl(file_path))
    return logs


def reload_logs(log_folder: str, interval: int = 5) -> None:
    """
    Reload logs from the specified folder at regular intervals.

    Args:
        log_folder: Path to the folder containing JSONL log files
        interval: Time interval (in seconds) to reload logs (default: 60)
    """
    global LOGS
    while True:
        LOGS = load_logs_from_folder(log_folder)
        time.sleep(interval)


def run_viewer(log_folder: str, port: int = 5000) -> None:
    """
    Run the log viewer with logs from the specified folder.

    Args:
        log_folder: Path to the folder containing JSONL log files
        port: Port number to run the server on (default: 5000)
    """
    global LOGS, LOG_DIR

    if not os.path.exists(log_folder):
        raise FileNotFoundError(f"Log folder not found: {log_folder}")

    # Set the log directory to the specified folder
    LOG_DIR = log_folder
    LOGS = load_logs_from_folder(log_folder)

    # Start a background thread to reload logs periodically
    reload_thread = threading.Thread(target=reload_logs, args=(log_folder,))
    reload_thread.daemon = True
    reload_thread.start()

    print(f"Loaded {len(LOGS)} log entries")
    print(f"Log viewer running at http://localhost:{port}")
    app.run(port=port, debug=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the log viewer")
    parser.add_argument("log_folder", help="Path to the folder containing JSONL log files")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the server on")

    args = parser.parse_args()
    run_viewer(args.log_folder, args.port)
'''