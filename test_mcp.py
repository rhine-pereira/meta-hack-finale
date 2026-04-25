import requests
import json

base_url = "http://localhost:7860/mcp"
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
}

# 1. Initialize
init_payload = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0.0"}
    },
    "id": 1
}
res = requests.post(base_url, headers=headers, json=init_payload)
print(f"Init Status: {res.status_code}")
session_id = res.headers.get("mcp-session-id")
print(f"Session ID: {session_id}")

# 2. Reset
headers["mcp-session-id"] = session_id
reset_payload = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "reset",
        "arguments": {
            "episode_id": "test-ep",
            "difficulty": 4,
            "seed": 42
        }
    },
    "id": 2
}
res = requests.post(base_url, headers=headers, json=reset_payload)
print(f"Reset Status: {res.status_code}")
print(f"Reset Body: {res.text}")
