"""Week 2：工具描述與分派 —— 模型提出，程式執行。

流程（兩筆 API 交易）：
1. 第一次呼叫帶 tools，取得模型建議的 tool_calls
2. 程式依 name / arguments 實際執行 http_get
3. 把結果以 role: "tool" 回填（tool_call_id 對應第一次的 id）
4. 第二次呼叫不帶 tools，取得最終 content

API key 從環境變數 NVIDIA_API_KEY 讀取（可放在 .env，勿提交）。
"""
import json
import os
from pathlib import Path

import requests

API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "minimaxai/minimax-m3.1-flash"
# 預設用教材的 NVIDIA 端點；若課堂允許改用其他 OpenAI 相容服務，可在 .env 設定 API_URL / MODEL 覆寫

HTTP_GET_TOOL = {
    "type": "function",
    "function": {
        "name": "http_get",
        "description": "Fetch a URL with HTTP GET. Return status code and a short body summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Absolute http(s) URL to fetch.",
                }
            },
            "required": ["url"],
        },
    },
}


def load_dotenv(path=".env"):
    """簡易 .env 載入：KEY=VALUE，不覆蓋已存在的環境變數。"""
    env_file = Path(__file__).with_name(path)
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def call_model(messages, tools=None):
    api_key = os.environ["NVIDIA_API_KEY"]
    payload = {
        "model": os.environ.get("MODEL", MODEL),
        "messages": messages,
        "max_tokens": 512,
        "temperature": 1,
        "top_p": 0.95,
    }
    if tools is not None:
        payload["tools"] = tools

    resp = requests.post(
        os.environ.get("API_URL", API_URL),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    print("status:", resp.status_code)
    data = resp.json()
    if not resp.ok:
        print("error:", data.get("error", data))
        raise SystemExit(1)
    return data["choices"][0]["message"]


def http_get(url):
    resp = requests.get(url, timeout=10)
    return {
        "status_code": resp.status_code,
        "body_summary": resp.text[:120],
    }


def dispatch(name, arguments):
    if name != "http_get":
        raise ValueError(f"unknown tool: {name}")
    args = json.loads(arguments)  # arguments 是 JSON 字串，要先解析
    return http_get(args["url"])


if __name__ == "__main__":
    load_dotenv()
    messages = [
        {
            "role": "user",
            "content": "用 http_get 抓取 https://example.com，然後用一句話說明你看到什麼。",
        }
    ]

    # 第一次 API 呼叫：帶 tools，期待拿到 tool_calls
    print("=== 第一次 API 呼叫（帶 tools）===")
    first = call_model(messages, tools=[HTTP_GET_TOOL])
    print("tool_calls:", json.dumps(first.get("tool_calls"), ensure_ascii=False, indent=2))
    if not first.get("tool_calls"):
        raise SystemExit("沒有拿到 tool_calls；先檢查工具描述與 user message。")

    # 工具執行與回填
    print("=== 工具執行 ===")
    messages.append(first)
    for call in first["tool_calls"]:
        print("tool_call_id:", call["id"])
        print("模型建議:", call["function"]["arguments"])
        result = dispatch(call["function"]["name"], call["function"]["arguments"])
        print("程式執行:", json.dumps(result, ensure_ascii=False))
        messages.append({
            "role": "tool",
            "tool_call_id": call["id"],
            "content": json.dumps(result, ensure_ascii=False),
        })

    # 第二次 API 呼叫：不帶 tools，只能根據 tool result 回答
    print("=== 第二次 API 呼叫（不帶 tools）===")
    print("回填的 tool message:", json.dumps(messages[-1], ensure_ascii=False))
    final = call_model(messages)
    print("reply:", final.get("content"))
