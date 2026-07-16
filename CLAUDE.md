# CLAUDE.md

本專案是「invest-advisor」投資決策 Agent:一個 Claude Code Skill(`invest-advisor/`)
加上一個預測總覽 Web Dashboard(`dashboard/`)。整體說明見根目錄 `README.md`。

## 專案地圖

| 路徑 | 內容 |
|------|------|
| `invest-advisor/SKILL.md` | skill 主流程 Step 1–6(觸發條件、資料蒐集、評分、報告、預測日誌) |
| `invest-advisor/references/` | 流程細則:question-types / scoring-rubric / report-templates / ta-checklist / crypto-specific / data-sources |
| `invest-advisor/scripts/` | 零第三方依賴的 Python 腳本(Python 3.10+,標準庫 only) |
| `invest-advisor/data/` | 資料層:market.db、news_cache.db、predictions.jsonl、reports/ |
| `invest-advisor/tests/` | pytest 測試套件 |
| `dashboard/backend/` | FastAPI(:8787),直接 import skill 的 `scripts/` 模組 |
| `dashboard/frontend/` | Next.js 16 + TypeScript + Tailwind v4(:3000) |
| `backup/` | 歷史報告備份(手動快照,勿當作報告目錄) |

## 常用指令

```bash
# 測試
cd invest-advisor && python -m pytest tests -q          # skill 單元測試
cd dashboard/backend && python -m pytest test_api.py -q # API 測試

# Dashboard 開發
cd dashboard/backend  && python -m uvicorn main:app --reload --port 8787
cd dashboard/frontend && npm run dev                     # http://localhost:3000
# Windows 一鍵:dashboard\start.ps1

# skill 資料腳本(於 invest-advisor/scripts/ 下執行)
python fetch_ohlcv.py --symbol TSLA,SPY --asset-type stock --timeframe 1d
python compute_ta.py --symbol TSLA --timeframe 1d
python verify_predictions.py --fetch
```

## 硬性規則(改動任何程式或文件前先確認)

1. **`data/predictions.jsonl` 是 append-only**:只能經 `log_prediction.py` 追加,
   禁止任何事後修改或重寫歷史;`outcomes.jsonl` 是衍生檔,每次驗證重建。
2. **報告唯一合法目錄是 `invest-advisor/data/reports/`**,命名
   `<YYYY-MM-DD>_<主題>_<Q1..Q6|calibration>.md`。不得自創目錄或命名;
   `backup/` 只是快照,不是輸出目標。
3. **技術指標只能由 `compute_ta.py` 產生**,禁止目測/心算;新聞快取只能經
   `cache_news.py` 讀寫,禁止手寫 SQL 動 `news_cache.db`。
4. **修改 `references/scoring-rubric.md` 的任何權重或錨點必須遞增
   rubric_version**,並同步 `scripts/common.py` 中的版本號。
5. **`scripts/` 保持零第三方依賴**(標準庫 only),新腳本亦同;dashboard
   backend 的依賴列在 `dashboard/backend/requirements.txt`。
6. **Dashboard 對 skill 資料只讀不寫**;後端新邏輯盡量放回 skill 的 `scripts/`
   模組再 import(單一事實來源),並在 `test_api.py` 補測試。
7. TWSE/TPEx 端點有速率限制,`fetch_chips.py` 已內建 2 秒間隔,
   **不得**繞過腳本直接高頻呼叫官方 API。

## Skill 行為約定(回答投資問題時)

- 任何投資相關問題都必須觸發 `invest-advisor` skill,先依 `SKILL.md`
  Step 0 判斷模式:**決策問題**走完 Step 1–6 不可跳步(歷史回顧、多空對辯、
  參考資料來源清單、預測日誌皆為必要);**純提問**走 Q0 快問模式
  (按需跑腳本取數+轉述過往決策,不產報告不記預測,禁止給新評分或新建議;
  模糊時預設 Q0)。
- 缺「白話摘要」「參考資料來源」或「掛單表」任一節的報告視為未完成:
  禁止存檔、禁止記錄預測。
- 所有輸出附非投資建議聲明;信心不足時誠實調降信心指數。

## 前端注意事項

`dashboard/frontend/` 使用的 Next.js 版本與訓練資料可能不同——寫任何前端程式前,
先讀 `dashboard/frontend/node_modules/next/dist/docs/` 內的對應文件
(見 `dashboard/frontend/AGENTS.md`)。前端只依賴 `NEXT_PUBLIC_API_URL`
環境變數指向後端;CORS 允許清單在 `dashboard/backend/main.py` 頂部。

## 文件對應

- 使用者導向的完整說明:根目錄 `README.md`
- skill 安裝、腳本參數、驗證框架細節:`invest-advisor/README.md`
- dashboard API 契約與擴充指引:`dashboard/README.md`
