# 📈 invest-advisor — 股票與加密貨幣決策顧問 Skill

Claude Code Skill:對投資決策問題進行多源資訊蒐集(新聞消息面、確定性技術分析、基本面/鏈上數據、宏觀環境),產出一份含 **1–100 量化評分**的 Markdown 決策報告,並自動將每次判斷寫入預測日誌,讓時間揭曉答案、用統計驗證這套系統是否誠實。

> ⚠️ 所有輸出皆為 AI 綜合公開資訊之分析,**非投資建議**;不做自動下單,最終決策與風險由使用者承擔。

---

## 一、如何使用

### 安裝

skill 需位於 `~/.claude/skills/invest-advisor`。本專案已透過 NTFS junction 安裝:

```powershell
New-Item -ItemType Junction `
  -Path   "C:\Users\<you>\.claude\skills\invest-advisor" `
  -Target "D:\coding\stock-agent\invest-advisor"
```

junction 讓開發目錄與安裝目錄是同一份檔案——改開發目錄即時生效。
(其他機器亦可直接複製整個資料夾;唯一環境需求:Python 3.10+,無第三方套件。)

### 觸發方式

**不需要任何指令**。在 Claude Code 對話中直接用自然語言提問,只要問題涉及投資決策(甚至只是提到股票代號/幣種名稱並詢問看法),skill 就會自動觸發。

### 五類問題與範例提問

| 類型 | 範例提問 | 你會得到什麼 |
|------|---------|-------------|
| **Q1 短期買進判斷** | 「現在能買 TSLA 嗎?」<br>「ETH 現在可以進場做多嗎?」 | 四維度分析 + **交易計畫表**(進場區間 / 止損 / 止盈 1、2 / 風險報酬比)。R:R < 1.5 時會直接建議等待,並告訴你等到什麼條件才值得進 |
| **Q2 長期持有判斷** | 「NVDA 適合長期持有三年嗎?」<br>「SOL 能長抱嗎?」 | 6 個月與 12 個月的多頭論點、論點依賴的關鍵假設、合理估值區間,以及**失效條件**(什麼事件發生時應該離場) |
| **Q3 標的推薦** | 「最近有什麼短期值得投資的美股?」<br>「推薦幾個長期看好的加密貨幣」 | 篩選漏斗(初選 8–12 檔 → 淘汰至 3–5 檔 → 完整評分)後的排序表,每檔含進場參考位與**主要風險**(強制欄位,不會只給多頭理由) |
| **Q4 點位分析** | 「BTC 現在的點位怎麼看?」<br>「AAPL 支撐壓力在哪?」 | 多時框技術分析(週線定方向 → 日線定結構 → 加密貨幣加 4H)+ **情境樹**:突破/回踩/跌破三條路徑,各含觸發價位與對應行動 |
| **Q5 資產配置** | 「我 60% TSLA、30% BTC、10% 現金,怎麼調整?」 | 先確認你的風險承受度、投資期限、流動性需求(缺了會先問),再給曝險分析(集中度 >25% 標紅)與**調整前 vs 調整後對比表**,每個動作附理由 |

### 讀懂報告中的兩個分數

- **推薦指數(1–100)**:四維度加權總分,代表「此方向的吸引力」。
  80–100 強烈看多 ｜ 60–79 偏多 ｜ 40–59 中性觀望 ｜ 20–39 偏空 ｜ 1–19 強烈看空
- **信心指數(1–100)**:獨立於方向,代表「資訊完整度 × 訊號一致性」。
  訊號互相矛盾、冷門標的資料稀缺、關鍵數字只有單一來源 → 信心會被規則強制調降(規則寫死在 `references/scoring-rubric.md` §IV,不允許無理由的高信心)。**信心 < 40 的報告會明說「參考價值有限」——請當作它真的有限。**

每份報告尾端有一行隱藏的 `prediction-meta` JSON,skill 會自動把它記入 `data/predictions.jsonl`——這是下方驗證框架的原料,不需要你做任何事。

### 報告存檔與 Dashboard 查詢

- **每份決策報告都會自動存檔**至 `data/reports/<日期>_<主題>_<題型>.md`
  (如 `2026-07-04_TW-screener_Q3.md`),隨時可回看。
- **Web Dashboard(推薦)**:前後端分離網頁(FastAPI + Next.js),位於
  `D:\coding\stock-agent\dashboard\`,詳見該目錄的 README:

  ```powershell
  cd D:\coding\stock-agent\dashboard
  .\start.ps1     # 一鍵啟動後端(:8787)+ 前端(:3000)+ 開瀏覽器
  ```

  網頁上可直接按「🔄 執行驗證」按鈕完成驗證並刷新,不需下指令。

- **靜態 HTML 備援(零依賴,不需 Node)**:

  ```bash
  python scripts/dashboard.py        # 產出 data/dashboard.html,瀏覽器直接開
  python scripts/dashboard.py --text # 不開瀏覽器,終端印精簡表格
  ```

  Dashboard 內容(兩版相同):
  1. **預測總表**——每筆預測的標的、方向、推薦/信心分數、進場區/SL/TP、
     R:R、目前狀態(彩色標籤)、**到期倒數天數**,以及判定後的報酬率
  2. **到期提醒橫幅**——有預測已到期未驗證時,頂部顯示
     「⏰ 有 N 筆可驗證」並附上該執行的指令;全部處理完則顯示綠色 ✅
  3. **決策報告清單**——`data/reports/` 下所有歷史報告的連結,點開即回看

### 驗證你收到的推薦(事後對答案)

每筆預測都有 horizon(如 Q1/Q3 短期 = 14 天)。到期後(或任何時候)執行:

```bash
python scripts/verify_predictions.py --fetch
```

- `--fetch` 先自動更新所有相關標的 + benchmark 的 K 線,再判定,一行完成
- **提早跑也有意義**:價格若已先觸及止盈/止損會提前結案;未到期未觸及則顯示 PENDING
- 也可以直接在對話裡說「驗證一下之前的推薦」,由 skill 代跑並解讀
- 跑完再執行一次 `dashboard.py`,總表就會顯示最新判定結果

各狀態的意義:

| 狀態 | 意義 | 計入勝率? |
|------|------|:---:|
| WIN | 先觸及止盈 TP1 | ✅ |
| LOSS | 先觸及止損(同根 K 棒雙觸也保守判 LOSS) | ✅ |
| FLAT | 進場了但到期都沒觸及,以期末價入帳 | 計入報酬,不計勝率 |
| NOT_FILLED | 價格從未進入建議進場區 | ❌(排除) |
| OPEN / PENDING | 尚未到期,持續追蹤 | — |
| NO_DATA | 本地缺 K 線 → 用 `--fetch` 補 | — |

### 用對話完成驗證與開 View(免打指令)

以上所有動作都不需要自己敲指令——直接在 Claude Code 對話中用自然語言說即可,skill 會代你執行對應腳本並解讀結果:

| 你可以這樣說 | skill 會做什麼 |
|------|------|
| 「3030 支撐在哪?」「外資最近買 0050 嗎?」「上次為什麼叫我等?」 | **Q0 快問**:依問題按需跑對應腳本(compute_ta / fetch_chips / recall_history…)取新鮮數據,結合過往決策直接回答——不產報告、不記預測;追問到「能不能買」才升級完整流程 |
| 「分析今天的 0050」「今日日報」 | Q6 日報:先驗證前次決策(`verify_predictions.py --fetch` 收盤級判定 + 現價對照掛單/SL/TP/失效條件),再更新今日點位;未指名標的 → `watchlist.py` 列出關注清單逐檔跑 |
| 「驗證一下之前的推薦」「對個答案」「上次推的表現如何?」 | 執行 `verify_predictions.py --fetch`(自動更新 K 線 → 判定 WIN/LOSS),並用白話解讀每筆結果與整體勝率 |
| 「開 dashboard」「我要看預測總覽」「有哪些預測到期了?」 | 啟動 Web Dashboard(`dashboard\start.ps1`)並開啟 http://localhost:3000;Node 環境不可用時退回靜態版 `dashboard.py` |
| 「看我的預測紀錄」 | 讀取 `data/predictions.jsonl`,整理成表格摘要 |
| 「看上次的台股報告」「列出歷史報告」 | 列出/開啟 `data/reports/` 下的決策報告 |
| 「這套評分系統準嗎?」「產出校準報告」 | 執行 `calibration_report.py`(建議累積 ≥ 50 筆已判定預測後再看) |
| 「清一下過期快取」 | 執行 `cache_gc.py` |

> 驗證與查看是唯讀/衍生操作,隨時可跑;`predictions.jsonl` 本身
> append-only,任何指令都不會改動歷史預測。

---

## 二、運作原理(為什麼這樣設計)

```
提問 → [1]問題分類 → [2]資訊蒐集 → [3]交叉驗證 → [4]評分 → [5]報告 → [6]寫入預測日誌
```

三個關鍵設計:

1. **技術指標零幻覺**:LLM 不目測 K 線、不心算 RSI。歷史 K 線存在本地
   `data/market.db`(SQLite),指標由 `scripts/compute_ta.py` 純 Python 確定性計算,
   LLM 只讀一行 JSON 結果。同時省下大量 token(約 15k → 200)。
2. **Freshness Gate 防過時**:每類資料有明確 TTL——歷史 K 線永久(歷史不變)、
   新聞摘要 24h、基本面到下次財報日;**即時價格與盤中新聞永遠現抓、永不快取**。
   帶著過時資料的檢索會產生「有憑有據的錯誤」,比無知更危險。
3. **每個判斷可證偽**:報告強制附「失效條件」,每筆預測記入 append-only 日誌,
   到期後用實際價格路徑判定 WIN/LOSS——系統好不好,由統計說話,不由自己說。

---

## 三、腳本手動使用(進階)

skill 平常會自己呼叫這些腳本;你也可以手動執行。全部位於 `scripts/`,零第三方依賴。

### 資料抓取與指標計算

```bash
cd invest-advisor/scripts

# 抓歷史 K 線(增量更新,已有的只補新資料)
python fetch_ohlcv.py --symbol TSLA,SPY --asset-type stock  --timeframe 1d
python fetch_ohlcv.py --symbol BTC,ETH  --asset-type crypto --timeframe 4h --days 120

# 計算技術指標快照(需先抓好資料)
python compute_ta.py --symbol TSLA    --timeframe 1d
python compute_ta.py --symbol BTCUSDT --timeframe 4h
```

- 資料來源:股票 = Yahoo Finance v8 API(1d/1w);加密貨幣 = Binance 公開 REST(1d/4h/1w)。皆免 API key。
- 股票**沒有** 4h(免費來源無可靠盤中歷史);加密貨幣符號自動轉 USDT 交易對(`BTC` → `BTCUSDT`)。
- compute_ta 輸出:趨勢分類、SMA20/50/200、RSI14、MACD、ATR14、量能比、52 週高低、最近三個支撐/壓力位。資料過時(stale_bars > 3)會警告。

### 驗證框架(檢討這套系統的績效)

```bash
# 每週跑:對到期預測判定 WIN / LOSS / FLAT / NOT_FILLED,輸出勝率、期望值(R)、
# 方向準確率、對 benchmark(股票 SPY / 加密 BTC)的超額報酬
# --fetch 會先自動更新所有相關標的與 benchmark 的 K 線,一鍵完成
python verify_predictions.py --fetch

# 產出 HTML 總覽(data/dashboard.html,瀏覽器直接開):
# 每筆預測的狀態/到期倒數/「可驗證」提醒 + 歷史決策報告清單
python dashboard.py            # 加 --text 同時印出終端表格

# 每 50 筆或每月跑:信心校準表 + Brier Score、推薦指數單調性、牛熊盤整分層
# 報告輸出至 data/reports/<日期>_calibration.md
python calibration_report.py

# 清理過期快取(新聞 24h、標的檔案 30d;絕不動 K 線與預測日誌)
python cache_gc.py            # 加 --dry-run 只看不刪

# Q6 日報的關注清單:仍有未到期預測的標的 + 每筆的驗證狀態
python watchlist.py                       # 全部
python watchlist.py --analyzed-within 14  # 只列近 14 天分析過的(總覽日報預設)
```

判定規則刻意保守:先觸止損判 LOSS、同一根 K 棒同時碰到止損與止盈也判 LOSS、價格從未進入進場區間判 NOT_FILLED(不計入勝率)、到期未平倉以期末價入帳(不丟棄,防倖存者偏差)。

**建議的每週例行流程**(兩行搞定):

```bash
python verify_predictions.py --fetch   # 更新 K 線 + 判定到期預測
python dashboard.py                    # 重新產出總覽,瀏覽器查看最新狀態
```

```bash
# 手動補記一筆預測(通常不需要,skill 會自動記)
python log_prediction.py --file pred.json

# 事件檔:報告中的重要事件與關鍵日期(skill 會自動記;規格見 report-templates.md)
python log_events.py --file events_payload.json   # 合併寫入 data/events.json
python log_events.py --show --symbol 3030.TW      # 查看目前事件(可過濾標的)
```

### 測試與評測

```bash
python -m pytest tests -q     # 78 個單元測試(指標計算、判定邏輯、schema 驗證、校準統計、dashboard)
```

`evals/eval-cases.md` 有 10 個標準測試提問 + 3 個反事實測試(如餵矛盾資訊檢查信心是否下降),用於人工評測 skill 輸出品質。

---

## 四、目錄結構

```
invest-advisor/
├── SKILL.md                    # 觸發條件 + 主流程(skill 本體)
├── README.md                   # 本文件
├── references/                 # 細則(依 Progressive Disclosure 按需載入)
│   ├── question-types.md       #   六類問題的個別流程(含 Q6 日報)
│   ├── scoring-rubric.md       #   評分錨點、權重、信心規則(rubric v1.1.0)
│   ├── ta-checklist.md         #   compute_ta 輸出判讀、多時框合成
│   ├── crypto-specific.md      #   鏈上、資金費率、BTC 主導率
│   ├── report-templates.md     #   各題型輸出模板 + prediction-meta 規格
│   └── data-sources.md         #   來源優先序、TTL、降級路徑
├── scripts/                    # 零依賴 Python 腳本(fetch/compute/log/verify/watchlist…,見上)
├── data/
│   ├── market.db               # SQLite:OHLCV / 基本面 / 標的檔案
│   ├── news_cache.db           # 新聞摘要快取(24h TTL)
│   ├── predictions.jsonl       # 預測日誌(append-only,禁止事後修改)
│   ├── outcomes.jsonl          # 判定結果(衍生檔,每次驗證重建)
│   ├── events.json             # 重要事件 + 關鍵日期(log_events.py 維護,dashboard 圖形化)
│   ├── dashboard.html          # 靜態版 view 產物(非報告)
│   └── reports/                # 唯一報告目錄:<日期>_<主題>_<Q1..Q6|calibration>.md
├── assets/report-template.md   # 報告骨架
├── evals/eval-cases.md         # 10 個評測案例
└── tests/                      # pytest 測試套件
```

---

## 五、已知限制

1. **資料延遲**:現價來自網路搜尋,可能延遲數分鐘至數小時 → 不適用當沖級決策。
2. **分數不是 alpha**:評分是公開資訊的結構化綜合;LLM 不具真正預測能力,有效市場下持續超額報酬本質困難——這正是驗證框架與 benchmark 對照存在的理由。
3. **樣本數**:預測累積 < 50 筆前,勝率等統計的信賴區間極寬,校準報告會自動加註警語,勿過早下結論。
4. **新聞污染**:情緒面易受帶風向文章影響;關鍵數字一律雙來源交叉驗證。
