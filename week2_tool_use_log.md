# Week 2：一次完整 tool-use 對話紀錄

- 程式：`week2_tool_dispatch.py`
- 執行日期：2026-11-23
- 任務（user message）：`用 http_get 抓取 https://example.com，然後用一句話說明你看到什麼。`

> **服務說明**：教材指定 NVIDIA（`minimaxai/minimax-m3.1-flash`），但我的 NVIDIA 帳號目前顯示「API Access Unavailable」需等待驗證，
> 因此改用同樣相容 OpenAI Chat Completions 的 Groq 執行，程式邏輯未改，只透過 `.env` 覆寫 `API_URL` 與 `MODEL`：
>
> - Endpoint：`POST https://api.groq.com/openai/v1/chat/completions`
> - Model：`openai/gpt-oss-120b`
> - API key 由 `.env` 載入，未寫入程式、未提交，以下紀錄不含金鑰。

## 觀察表

| 步驟 | 模型建議 | 程式實際執行 |
|---|---|---|
| 第一次 API 回應 | `status: 200`；`name: http_get`，`arguments: {"url":"https://example.com"}`，`id: fc_a0cbac18-bf99-46cc-ba30-30dfcee28cf3` | 尚未執行；只收到建議 |
| 工具執行 | 無 | `status_code: 200`，`body_summary`（前 120 字）：`<!doctype html><html lang=en><head><meta charset=utf-8><link rel=icon href=data:,><meta name=viewport content="width=dev` |
| 第二次 API 請求 | 無 | 回填 `role: "tool"`，`tool_call_id: fc_a0cbac18-bf99-46cc-ba30-30dfcee28cf3`（與第一次的 id 相同）；請求不帶 `tools` |
| 第二次 API 回應 | 無 | `status: 200`；`choices[0].message.content`：我看到一個簡潔的示例網頁，顯示了「Example Domain」的標題與說明文字，並提供指向 IANA 網站的連結。 |

## 完整執行輸出

```text
=== 第一次 API 呼叫（帶 tools）===
status: 200
tool_calls: [
  {
    "id": "fc_a0cbac18-bf99-46cc-ba30-30dfcee28cf3",
    "type": "function",
    "function": {
      "name": "http_get",
      "arguments": "{\"url\":\"https://example.com\"}"
    }
  }
]
=== 工具執行 ===
tool_call_id: fc_a0cbac18-bf99-46cc-ba30-30dfcee28cf3
模型建議: {"url":"https://example.com"}
程式執行: {"status_code": 200, "body_summary": "<!doctype html><html lang=en><head><meta charset=utf-8><link rel=icon href=data:,><meta name=viewport content=\"width=dev"}
=== 第二次 API 呼叫（不帶 tools）===
回填的 tool message: {"role": "tool", "tool_call_id": "fc_a0cbac18-bf99-46cc-ba30-30dfcee28cf3", "content": "{\"status_code\": 200, \"body_summary\": \"<!doctype html><html lang=en><head><meta charset=utf-8><link rel=icon href=data:,><meta name=viewport content=\\\"width=dev\"}"}
status: 200
reply: 我看到一個簡潔的示例網頁，顯示了「Example Domain」的標題與說明文字，並提供指向 IANA 網站的連結。
```

## 觀察與自我檢查

- **模型建議的 URL 在哪裡？** 在第一次回應的 `tool_calls[0].function.arguments`，值是 JSON 字串 `"{\"url\":\"https://example.com\"}"`，程式用 `json.loads` 解析後才取得 `url`。
- **程式用哪個函式真的發出請求？** `http_get()` 內的 `requests.get(url, timeout=10)`；`dispatch()` 依 `name` 決定呼叫哪個工具。模型本身沒有連到 example.com。
- **`tool_call_id` 對不上會發生什麼？** 模型無法把結果對應到它提出的建議，API 通常會回 400 錯誤，指出 tool message 找不到對應的 tool call。
- **為什麼第二次呼叫不帶 `tools`？** 讓模型看不到工具，只能根據回填的 tool result 產生最終 `content`，不會再提出新的工具呼叫。
- **額外觀察**：`body_summary` 只有前 120 字（還沒到 `<title>`），但模型回答提到「Example Domain」標題與 IANA 連結，這些資訊不在回填結果中，推測來自模型對 example.com 的既有知識，而不是這次工具的實際觀察。
