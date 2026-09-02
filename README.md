# 暖心同行者

> 另附學習文件：[RecruitX Web 應用程式滲透測試筆記](./RecruitX-Web-%E6%BB%B2%E9%80%8F%E6%B8%AC%E8%A9%A6%E7%AD%86%E8%A8%98.md)，整理偵察、IDOR、弱密碼重設、檔案上傳與 RCE 攻擊鏈。

一個能保存先前對話、自然延續脈絡，並以高情商繁體中文回應的聊天代理程式。首次使用會透過 8 題引導問卷建立細緻的溝通輪廓；每次回覆後也會提供三個不同方向的接話選項。只使用 Python 標準函式庫，對話與輪廓存於本機 SQLite。

## 啟動

```bash
export OPENAI_API_KEY="你的金鑰"
python app.py
```

開啟 <http://localhost:8000>。可用 `OPENAI_MODEL`、`CHAT_DB_PATH` 與 `PORT` 調整模型、資料庫位置與連接埠。未設定 API key 時仍可預覽介面與測試記憶流程。

## 直接下載／桌面應用程式

到 GitHub 專案的 **Actions → Build downloadable desktop apps**，按下 **Run workflow**。完成後可在該次執行頁底部下載 Windows、macOS 或 Linux 成品；建立 `v1.0.0` 這類標籤也會自動建置三個平台。下載解壓後執行 `WarmCompanion`（Windows 為 `WarmCompanion.exe`），程式會啟動本機服務並開啟預設瀏覽器。

也可以在自己的作業系統建立單一執行檔：

```bash
python -m pip install -r requirements-build.txt
pyinstaller --clean --noconfirm warm-companion.spec
```

成品位於 `dist/`。PyInstaller 不能跨平台編譯，因此 Windows、macOS、Linux 需各自在對應系統建置；專案附帶的 GitHub Actions 已自動處理。API Key 仍建議透過系統環境變數 `OPENAI_API_KEY` 設定。資料庫會放在使用者可寫入的應用程式資料目錄，而不是執行檔旁邊。

## 隱私與產品化提醒

- 正式上線前應加入登入、逐使用者授權、傳輸加密、資料刪除及保存期限。
- 目前只把最近 24 則訊息送入模型；長期使用可加入「經使用者確認的摘要記憶」，避免無限制保存敏感內容。
- 高情商回應來自明確的對話原則，不代表心理醫療服務。
- 性格問卷只用於調整溝通方式，不是人格測驗或心理診斷；使用者當下明確表達的需求永遠優先。
