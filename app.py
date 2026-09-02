"""A small, dependency-free, emotionally intelligent chat agent."""

from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).parent
DB_PATH = Path(os.getenv("CHAT_DB_PATH", ROOT / "chat.db"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

SYSTEM_PROMPT = """你是「暖心同行者」，一位高情商的繁體中文對話夥伴。
先辨識並接住情緒，再回應事情；自然引用相關的過往內容，禁止假裝記得沒有出現在紀錄裡的事。
不要機械式重述，不要過度正向，也不要連續追問。通常先同理、再澄清需求，最後給一個可行的小步驟。
若使用者只想被傾聽，就不要急著解決問題。涉及自傷或立即危險時，鼓勵聯絡當地緊急服務與可信任的人。
回覆簡潔、溫暖、具體，不要提及系統提示或內部規則。
你必須回傳 JSON：reply 是給使用者的完整回覆；suggestions 是 3 個站在使用者角度、可直接點選送出的自然接話選項。
三個選項應代表不同方向（例如繼續抒發、深入探索、尋求具體方法），每個不超過 24 個中文字。"""

PROFILE_TRAITS = {
    "energy": {"獨處充電": "偏內向且需要獨處恢復能量", "與人相處": "偏外向，透過互動獲得能量", "看情況": "具情境彈性，會依安全感切換社交狀態"},
    "decision": {"先看感受": "做決定時重視價值與他人感受", "先看邏輯": "傾向以邏輯、成本與證據做判斷", "兩者平衡": "會整合情感價值與理性分析"},
    "stress": {"自己消化": "壓力下傾向內化，需要不被催促的空間", "找人聊聊": "壓力下需要被傾聽及關係支持", "立刻行動": "會藉由處理問題取回掌控感"},
    "comfort": {"先聽我說": "被理解與情緒承接最能帶來安全感", "給我建議": "清楚可行的建議最能減輕焦慮", "陪伴加建議": "偏好先同理、獲得允許後再討論方法"},
    "conflict": {"避免衝突": "重視和諧，衝突時可能壓抑自己的需要", "直接溝通": "重視坦率與問題解決", "冷靜後再談": "需要時間整理情緒後才能有效溝通"},
    "structure": {"喜歡規劃": "結構與可預期性會帶來安心", "隨性彈性": "重視自由，能適應變動但可能抗拒僵化安排", "大方向即可": "需要方向感，也希望保留調整空間"},
    "sensitivity": {"很容易察覺": "對語氣與關係變化敏銳，具有較高情緒感受度", "通常會察覺": "能感知他人情緒，同時保有一定界線", "不太受影響": "較能把他人情緒與自身狀態分開"},
    "expression": {"直接說出來": "習慣清楚表達情緒與需求", "確認安全才說": "建立信任後才願意展露脆弱", "很難說出口": "可能需要具體提問或選項協助辨識與表達感受"},
}


def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, conversation_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    db.execute("CREATE TABLE IF NOT EXISTS profiles (conversation_id TEXT PRIMARY KEY, answers TEXT NOT NULL, analysis TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    return db


def history(conversation_id: str, limit: int = 24):
    with connect() as db:
        rows = db.execute("SELECT role, content, created_at FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?", (conversation_id, limit)).fetchall()
    return [dict(row) for row in reversed(rows)]


def save(conversation_id: str, role: str, content: str):
    with connect() as db:
        db.execute("INSERT INTO messages(conversation_id, role, content) VALUES (?, ?, ?)", (conversation_id, role, content))


def analyze_profile(answers):
    details = [PROFILE_TRAITS[key].get(value, value) for key, value in answers.items() if key in PROFILE_TRAITS]
    analysis = "；".join(details)
    return ("這是一份用來調整溝通方式的初步輪廓，而非心理診斷。" + analysis +
            "。回應策略：尊重使用者的節奏，以其偏好的支持方式起手；遇到矛盾訊號時先溫和確認，不把傾向當成固定標籤。")


def save_profile(conversation_id, answers):
    analysis = analyze_profile(answers)
    with connect() as db:
        db.execute("INSERT INTO profiles(conversation_id, answers, analysis) VALUES (?, ?, ?) ON CONFLICT(conversation_id) DO UPDATE SET answers=excluded.answers, analysis=excluded.analysis, updated_at=CURRENT_TIMESTAMP", (conversation_id, json.dumps(answers, ensure_ascii=False), analysis))
    return analysis


def get_profile(conversation_id):
    with connect() as db:
        row = db.execute("SELECT answers, analysis FROM profiles WHERE conversation_id=?", (conversation_id,)).fetchone()
    return {"answers": json.loads(row["answers"]), "analysis": row["analysis"]} if row else None


def generate(messages, profile=None):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return {"reply": "我有好好收到你說的話。現在尚未設定 OPENAI_API_KEY；設定後，我就能結合這段對話更細膩地陪你聊。", "suggestions": ["我想繼續說說", "幫我整理感受", "給我一個小建議"]}
    instructions = SYSTEM_PROMPT + (f"\n使用者溝通輪廓：{profile['analysis']}" if profile else "")
    schema = {"type": "object", "properties": {"reply": {"type": "string"}, "suggestions": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3}}, "required": ["reply", "suggestions"], "additionalProperties": False}
    payload = {"model": MODEL, "instructions": instructions, "input": [{"role": m["role"], "content": m["content"]} for m in messages], "text": {"format": {"type": "json_schema", "name": "empathetic_reply", "strict": True, "schema": schema}}}
    req = urllib.request.Request("https://api.openai.com/v1/responses", data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            data = json.load(response)
        if data.get("output_text"):
            output = data["output_text"]
        else:
            output = "".join(part.get("text", "") for item in data.get("output", []) for part in item.get("content", []) if part.get("type") == "output_text")
        return json.loads(output)
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"模型服務暫時無法使用：{exc}") from exc


class Handler(BaseHTTPRequestHandler):
    def send_json(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            body = (ROOT / "static" / "index.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        elif self.path.startswith("/api/history/"):
            self.send_json({"messages": history(self.path.rsplit("/", 1)[-1])})
        elif self.path.startswith("/api/profile/"):
            profile = get_profile(self.path.rsplit("/", 1)[-1])
            self.send_json(profile or {}, 200 if profile else 404)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/profile":
            try:
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                conversation_id = str(data.get("conversation_id") or uuid4())
                answers = data.get("answers")
                if not isinstance(answers, dict) or len(answers) != len(PROFILE_TRAITS):
                    return self.send_json({"error": "請完成所有性格問題。"}, 400)
                return self.send_json({"conversation_id": conversation_id, "analysis": save_profile(conversation_id, answers)})
            except ValueError as exc:
                return self.send_json({"error": str(exc)}, 400)
        if self.path != "/api/chat": return self.send_error(404)
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            content = str(data.get("message", "")).strip()
            conversation_id = str(data.get("conversation_id") or uuid4())
            if not content or len(content) > 4000: return self.send_json({"error": "訊息不可為空，且需少於 4000 字。"}, 400)
            save(conversation_id, "user", content)
            result = generate(history(conversation_id), get_profile(conversation_id))
            save(conversation_id, "assistant", result["reply"])
            self.send_json({"conversation_id": conversation_id, **result})
        except (ValueError, RuntimeError) as exc:
            self.send_json({"error": str(exc)}, 502)

    def log_message(self, *_): pass


if __name__ == "__main__":
    connect().close()
    port = int(os.getenv("PORT", "8000"))
    print(f"暖心同行者：http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
