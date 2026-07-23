---
name: invest-advisor
description: >
  股票與加密貨幣決策顧問。當使用者詢問任何投資決策相關問題時必須使用此 skill,
  包括:是否買進/賣出某股票或幣種、某標的能否長期持有、推薦短期/長期投資標的、
  分析某標的的進場點位/止盈/止損、資產配置建議與再平衡。
  即使使用者只是提到股票代號、幣種名稱並詢問看法,也應觸發此 skill;
  純資訊提問(問價位/支撐/籌碼/營收/過往決策,如「3030 支撐在哪」
  「外資最近買 0050 嗎」)同樣觸發,走 Q0 快問模式以腳本取數後直接回答。
  決策問題會執行資訊蒐集(新聞、技術分析、基本面)並產出含 1-100 量化
  評分的 Markdown 決策報告,同時自動記錄預測日誌供事後驗證。
---

# invest-advisor:投資決策顧問

產出一份含量化評分(1–100)的 Markdown 決策報告,並將每次判斷寫入
append-only 預測日誌,讓時間揭曉答案。**不做自動下單;所有輸出皆非投資建議。**

## 主流程(決策問題走完全部步驟;純提問走 Step 0 快問模式)

### Step 0 — 模式判斷(快問 vs 決策報告)

先判定使用者要的是**決策**還是**資訊**:

- **決策問題**(能不能買/賣、點位與進出場建議、標的推薦、配置調整、
  日報追蹤)→ 進 Step 1 分類為 Q1–Q6,走完整流程,產出報告
- **純提問(Q0 快問)**(問事實、狀態、解釋、過往決策:「支撐在哪」
  「外資最近買嗎」「上次為什麼叫我等」「上月營收多少」)→
  走 `references/question-types.md` 的 **Q0 快問模式**:
  **依問題按需跑對應腳本取新鮮數據 + recall 過往決策**,直接回答,
  不產報告、不存檔、不記預測
- **分不清時(「3030 現在怎樣?」)→ 預設 Q0 快問**,回答結尾附一句
  「需要完整決策報告嗎?」;使用者追問到決策(「所以能買嗎」)→
  立即升級走完整流程
- Q0 的資料紀律不打折:技術指標只能來自 compute_ta、籌碼只能來自
  fetch_chips、現抓新聞仍要回寫 cache_news;**觀點只能轉述既有報告的
  結論與其驗證狀態,禁止產生新評分、新方向、新點位建議**(細則見 Q0)

### Step 1 — 問題分類

先判定問題屬於哪一類,讀 `references/question-types.md` 取得該類的專屬流程:

| 類型 | 例句 | 側重 |
|------|------|------|
| Q1 短期買進 | 「現在能買 X 嗎」 | 技術+消息;必附進場/SL/TP 表 |
| Q2 長期持有 | 「X 能長抱嗎」 | 基本面+護城河;6/12 個月論點 |
| Q3 標的推薦 | 「推薦短期標的」 | 篩選漏斗,輸出 3–5 檔 |
| Q4 點位分析 | 「X 點位怎麼看」 | 多時框 TA + 情境樹 |
| Q5 資產配置 | 「配置怎麼調」 | 曝險分析 + 再平衡方案 |
| Q6 日報 | 「分析今天的 X」「今日日報」 | 先驗證前次決策(兩層)再更新今日觀點;未指名標的 → `watchlist.py` 取關注清單逐檔跑 |

### Step 1.5 — 歷史回顧(有標的必跑,不可省略)

分析前先查本 skill 對同一標的過去說過什麼:

```bash
python recall_history.py --symbol 2330.TW
```

- 輸出含:過去每筆預測(方向/分數/論點)+ 判定結果(WIN/LOSS/PENDING)
  + 同標的歷史報告檔名(到 `data/reports/` 讀取)
  + **全系統信心校準回饋 `calibration`**(各信心分桶的實際勝率;
    本筆信心落在 `overconfident_buckets` 內 → Step 4 依 rubric §IV
    校準回饋條款信心 −10)
- **有歷史紀錄時,報告必須包含「與上次觀點的差異」段落**:
  沿用、修正或翻轉,都要指明觸發變化的新事實;
  **觀點翻轉(long↔short)而說不出新事實 → 信心指數 −10**
- 歷史中同標的有 LOSS → 在報告中回顧當時論點錯在哪,避免重蹈
- `prediction_count = 0` → 報告註明「首次分析」即可
- Q3 篩選模式只對進入完整評分的存活者跑此步驟
- **Q6 日報在此步之後必須另跑 `python verify_predictions.py --fetch`**,
  做「收盤級正式判定 + 盤中現價對照」兩層驗證,並輸出前次決策驗證表
  (細節見 question-types.md Q6);日報**觀點有變才記新預測**
  (question_type = Q6_daily),沿用觀點不記,防止日誌灌水

### Step 2 — 資訊蒐集(本地優先 → 網路補足)

**Freshness Gate:先查本地,未過期直接用;過期或缺 → 現抓。**

| 資料 | 來源順序 | TTL |
|------|---------|-----|
| 歷史 K 線 | `market.db`(缺→跑 fetch_ohlcv.py) | 永久,增量更新 |
| 技術指標 | **只能**由 compute_ta.py 計算,禁止目測/心算 | 隨 K 線 |
| 現價、盤中新聞 | 永遠 WebSearch 現抓,標註查詢時間戳 | 不快取 |
| 新聞情緒摘要 | `cache_news.py --recall` → 不足再現抓 | 24h |
| 台股籌碼(法人/融資券) | **只能**由 fetch_chips.py 取得(入庫累積) | 歷史永久,增量 |
| 官方公告/月營收 | fetch_mops.py 現抓(MOPS 一手資料) | 不快取 |
| 基本面/鏈上 | fundamentals 表 → 過期現抓 | 至下次財報日 |

標準指令序(股票範例;加密貨幣把 asset-type 換成 crypto,並多抓 4h):

```bash
cd <skill 目錄>/scripts
python fetch_ohlcv.py --symbol TSLA,SPY --asset-type stock --timeframe 1d   # 含 benchmark
python fetch_ohlcv.py --symbol TSLA --asset-type stock --timeframe 1w
python compute_ta.py --symbol TSLA --timeframe 1d
python compute_ta.py --symbol TSLA --timeframe 1w
python compute_ta.py --symbol SPY --timeframe 1d    # benchmark TA:宏觀分數的大盤趨勢錨(rubric §II)
```

台股標的宏觀錨另跑 `^TWII` 或 `0050.TW`;加密貨幣用 BTCUSDT。

台股標的(.TW/.TWO)**必須**另跑(官方 A 級證據,見 rubric §0):

```bash
python fetch_chips.py --symbol 2330.TW    # 三大法人+融資券(上櫃僅法人)
python fetch_mops.py --symbol 2330.TW     # MOPS 重大訊息+月營收
```

- **benchmark 必抓**:股票同時更新 SPY,加密貨幣同時更新 BTC(驗證框架依賴)
- WebSearch 每標的最少 3 次、最多 8 次(新聞/財報/宏觀),依複雜度縮放;
  **其中至少 1 次必須是反向查詢**(如「{標的} 利空」「{標的} short thesis」),
  避免搜尋結果被單邊敘事主導
- **外媒對照**:權值股(台灣 50 成分等級)與國際高知名度標的,
  至少 1 次英文搜尋(Reuters/Bloomberg/WSJ 視角);外媒與本地媒體的
  溫差寫入 Step 3.5 多空對辯
- **ETF 標的必抓代理標的新聞**(0050/009816/00918/009824 等):
  ETF 沒有個股新聞,只引用大盤通稿等於消息面無證據。
  `python cache_news.py --recall <symbol> --with-proxies` 取自身 +
  代理標的(權重成分股 + 指數)快取,代理標的的新聞照樣要現抓補齊;
  對照表見 `references/data-sources.md` §3.1,報告須標明論據來自代理標的
- **新聞快取(讀寫都不可省略)**:搜尋前先
  `python cache_news.py --recall <symbol>` 取未過期摘要;搜尋完把本次新聞
  摘要整理成 JSON 陣列(每則含 symbol/headline/summary/sentiment/source_url)
  寫入暫存檔後執行 `python cache_news.py --save <items.json>`,
  讓下次分析與情緒軌跡比對有據可查
- **來源多樣性稽核(存檔後強制,禁止目測)**:
  `python cache_news.py --stats --symbol <symbol>` 取得
  `independent_sources`(去重網域)、`flags`、`confidence_penalty`;
  `weak_source_count`(< 3 個獨立來源)→ 先補搜尋,補不到才依
  rubric §IV −10 並在報告明說;`single_domain_dominant` → −5 且多空對辯
  註明敘事單邊;`no_foreign_source` 且為權值股/國際標的 → 補一次英文搜尋。
  結果寫入報告「參考資料來源」節(細則見 data-sources.md §4.1)
- 加密貨幣另讀 `references/crypto-specific.md`(資金費率、鏈上、恐懼貪婪)
- 資料稀缺的冷門標的 → 信心指數必須調降並明說原因

### Step 3 — 交叉驗證

- 關鍵數字(現價、財報數據)至少 2 個獨立來源;本地庫只計為一個來源
- 來源衝突時在報告中明確標註兩個數字與出處,不擅自取捨

### Step 3.5 — 多空對辯(評分前必做)

評分前先強制寫出對抗性的兩造論述,再裁決(降低確認偏誤;
借鑑多 agent 框架的 Bull/Bear Researcher + Debate Room 模式):

1. **多頭最強論點 × 3**:每條附具體證據(數據/新聞/指標,含來源)
2. **空頭最強論點 × 3**:同樣標準;**禁止立稻草人**——
   要寫「一個聰明的空頭會說什麼」,不是「容易反駁的空頭說什麼」
3. **裁決**:指出哪一方證據更強、為什麼;無法分辨強弱 → 這本身就是
   訊號矛盾,Step 4 信心指數照 rubric 調降

裁決結論必須與 Step 4 的推薦指數方向一致;不一致時回頭修正評分。

### Step 4 — 綜合評分

依 `references/scoring-rubric.md` 計算四維度分數與加權總分。
核心規則(細節見 rubric):

- 推薦指數 = 加權總分;信心指數獨立計算,反映資訊完整度 × 訊號一致性
- **技術面以主時框 compute_ta 的 `suggested_score` 區間為錨**,
  偏離要寫理由且 ≤ 10 分;**宏觀面的大盤趨勢必須引 benchmark TA**
  (皆為 rubric 1.2.0 機械錨定條款)
- **信心指數套用 Step 1.5 的校準回饋**:本筆信心所屬分桶被標記
  overconfident → 信心 −10(rubric §IV)
- **訊號矛盾或資料稀缺時,信心指數必須誠實調降;禁止預設高信心**
- 買點問題:**R:R < 1.5 必須主動建議放棄或等待**,不得硬給進場點

### Step 5 — 產出報告

依 `references/report-templates.md` 對應模板輸出;外框骨架見
`assets/report-template.md`。每份報告必含:**白話摘要(開頭第一節,
3–6 句給初學者的日常語言:看什麼/判斷什麼/建議怎麼做,規範見
report-templates.md「白話摘要規範」)**、四維度分數、多空對辯與裁決
(Step 3.5 產出)、**掛單表(限價掛單價+股數換算,規範見
report-templates.md「掛單表區塊」;觀望結論也要列被動限價單或條件單)**、
失效條件(可證偽)、風險聲明、**參考資料來源清單
(附完整 URL 與查詢日期,規範見 report-templates.md「來源標註規範」)**、
`prediction-meta` 隱藏 JSON 區塊;有歷史紀錄時另含「與上次觀點的差異」
(Step 1.5 產出)。

**硬性關卡:缺「白話摘要」「參考資料來源」或「掛單表」任一節的報告
視為未完成——禁止存檔、禁止進 Step 6 記錄預測。**同一對話的追問延伸報告
(第 2、3 份)同樣適用。

**報告除了在對話中呈現,必須同步存檔**,且**唯一合法目錄為
`<skill 目錄>/data/reports/`(與 predictions.jsonl 同一個 data/,
不是專案根目錄的 data/)**,命名 `<YYYY-MM-DD>_<主題>_<類型>.md`(如
`2026-07-04_TW-screener_Q3.md`)。完整存檔規範見
report-templates.md「存檔規範」一節——禁止自創目錄或命名。

### Step 5.5 — 事件萃取(有報告就要跑,不可省略)

報告存檔後,把報告中的**重要事件**與**關鍵日期和時間**整理成 payload JSON
(規格見 report-templates.md「事件萃取規格」),存暫存檔後執行:

```bash
python log_events.py --file <events_payload.json>
```

- **important_events(重要事件)**:已發生/已確認、影響判斷的事實
  (營收公告、法說結論、外資動向轉折、政策事件…),每則標多空影響
- **key_dates(關鍵日期和時間)**:報告提到的未來時點。其中**除息日/
  除權日、配息發放日,以及任何消息/公告的發布日**(財報、法說、月營收、
  重大訊息、政策/總經數據)與失效條件觀察期限屬**必記清單**——
  報告內文提到卻沒進 key_dates 視為本步驟未完成;
  不確定的日期標 `estimated`(完整清單見 report-templates.md 規則 3)
- 腳本自動去重與排序,重跑同標的只會更新既有事件,不會重複
- 產出檔 `data/events.json` 供 dashboard `/api/events` 圖形化呈現

### Step 6 — 寫入預測日誌(不可省略)

把報告尾端 prediction-meta 的 JSON 存檔後執行:

```bash
python log_prediction.py --file <meta.json>
```

腳本會做格式斷言(欄位、價格順序、R:R),失敗時修正報告後重試。
Q3 推薦的每一檔各記一筆。

## 驗證與查詢(使用者以自然語言要求時執行)

| 使用者說 | 動作 |
|------|------|
| 「驗證推薦」「對答案」「表現如何」 | 跑 `verify_predictions.py --fetch`,白話解讀每筆結果與統計 |
| 「開 dashboard」「預測總覽」「哪些到期了」 | 優先啟動 Web 版:執行 `D:\coding\stock-agent\dashboard\start.ps1`(FastAPI :8787 + Next.js :3000,會自動開瀏覽器;已啟動則直接開 http://localhost:3000)。Node 不可用時退回 `dashboard.py` 靜態版 |
| 「看預測紀錄」 | 讀 `data/predictions.jsonl` 整理成表格 |
| 「看歷史報告」 | 列出/開啟 `data/reports/*.md` |
| 「看重要事件」「最近有什麼關鍵日期」 | 跑 `log_events.py --show`(可加 `--symbol`),整理成表格 |
| 「評分系統準嗎」「校準報告」 | 跑 `calibration_report.py`(<50 筆時提醒樣本不足) |

```bash
python verify_predictions.py --fetch   # 每週:先自動更新 K 線再判定 WIN/LOSS
python dashboard.py                    # 產出 HTML 總覽(預測狀態/到期提醒/報告清單)
python calibration_report.py           # 每 50 筆或每月:校準+績效報告
python cache_gc.py                     # 清過期快取
```

發現系統性偏差 → 調整 scoring-rubric.md 權重並遞增 rubric 版本號。

## 已知限制(需在報告風險聲明中誠實揭露)

1. 資料延遲:價格可能延遲數分鐘至數小時,不適用當沖級決策
2. 分數是公開資訊的結構化綜合,不是 alpha 保證;LLM 不具真正預測能力
3. 新聞情緒易受帶風向文章污染(benchmark 對照正是為此存在)
4. 股票無免費 4h 資料:股票用 1d/1w 雙時框,4h 僅加密貨幣
5. 所有輸出皆非投資建議,最終決策與風險由使用者承擔

## 參考文件索引

| 檔案 | 何時讀 |
|------|--------|
| `references/question-types.md` | 每次,Step 1 分類後 |
| `references/scoring-rubric.md` | 每次,Step 4 評分前 |
| `references/report-templates.md` | 每次,Step 5 輸出前 |
| `references/ta-checklist.md` | 解讀 compute_ta.py 輸出時 |
| `references/crypto-specific.md` | 標的為加密貨幣時 |
| `references/data-sources.md` | 資料抓取失敗或來源衝突時 |
