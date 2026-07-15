# 報告輸出模板

外框骨架見 `assets/report-template.md`;本文件定義各題型的差異區塊與
prediction-meta 規格。**所有價位判斷以「現價查詢時間戳」為基準。**

## 存檔規範(強制,無例外)

- **唯一合法目錄:`data/reports/`**。禁止存到 skill 根目錄、`reports/`、
  專案根目錄或其他任何位置。
- **命名文法:`<YYYY-MM-DD>_<主題>_<類型>.md`**(日期在最前,底線分隔)
  - 主題:標的代號或短語,連字號串接,如 `TSLA`、`SOL-ONDO`、`TW-screener`
  - 類型:`Q1`–`Q5`(決策報告)或 `calibration`(校準報告)
  - 範例:`2026-07-04_TW-screener_Q3.md`、`2026-07-04_SOL-ONDO_Q1.md`、
    `2026-08-01_calibration.md`
- 同日同主題同類型第二份 → 加 `-2` 後綴:`2026-07-04_TSLA_Q1-2.md`
- `data/reports/` 只放報告;view 產物(如 `dashboard.html`)放 `data/`

## 共用外框(所有題型)

```markdown
# 【決策報告】{標的} — {題型名稱}
> 產出時間:{ISO timestamp}｜現價:${price}(來源:{src},查詢於 {ts})

## 一、結論摘要(TL;DR)
- 建議動作:{買進/持有/觀望/減碼/賣出/等待}
- 推薦指數:{n}/100 ｜ 信心指數:{m}/100
- 一句話理由

## 二、與上次觀點的差異   ← recall_history.py 輸出;首次分析寫「首次分析」
- 上次判斷:{日期}{方向}{推薦指數};結果 {WIN/LOSS/PENDING}
- 本次立場:{沿用/修正/翻轉},因為 {觸發變化的新事實}
- {歷史有 LOSS → 回顧當時論點錯在哪}

## 三、四維度分析
### 消息面({s1}/100)
### 技術面({s2}/100)   ← 數值只引 compute_ta 輸出,標註 as_of
### 基本面({s3}/100)
### 宏觀面({s4}/100)

## 四、多空對辯(SKILL.md Step 3.5)
### 多頭最強論點 ×3   ← 每條附證據與來源
### 空頭最強論點 ×3   ← 聰明空頭視角,禁止稻草人
### 裁決              ← 必須與推薦指數方向一致

## 五、{題型專屬區塊}

## 六、掛單表   ← 必附,規則見下方「掛單表區塊」

## 七、失效條件
- 失效條件:{可觀察、可證偽的具體條件,如「日線收破 232」}

## 八、風險聲明
本報告為 AI 綜合公開資訊之分析,非投資建議;資料可能延遲或有誤,
最終決策與風險由使用者自行承擔。{若信心 < 40:加註資訊不足警語}

## 九、參考資料來源   ← 必填,規則見下方「來源標註規範」
### 網路來源(標題+媒體+完整 URL+查詢日期+支持哪個論點)
### 本地資料(market.db/compute_ta 的 as_of、cache_news 命中數)
### 現價來源(兩個獨立來源;僅一個 → 依 rubric −10 並在此註明)

<!-- prediction-meta: {單行 JSON} -->
```

## 來源標註規範(強制,無例外)

1. **「九、參考資料來源」缺失或空泛的報告視為未完成**——
   不得存檔至 data/reports/、不得執行 log_prediction.py。
2. 消息面與基本面的**每個論據**必須能對應到來源清單中的一項;
   對應不到的論據刪除,不得留在報告裡。
3. 網路來源必附**完整 URL**;禁止「網路搜尋」「新聞報導」這類
   無法回查的模糊標註。追問延伸報告(同一對話的第 2、3 份)同樣適用,
   沿用前一份的來源也要重新列出。
4. 本地資料標 as_of 日期;現價維持雙來源規則(scoring-rubric §IV)。
5. 來源類型須可辨識:官方公告/交易所數據 > 財經媒體 > 券商行銷、
   訂閱自媒體(後者僅可作情緒佐證,不得作為評分的唯一依據)。

## 題型專屬區塊

### Q1 — 交易計畫表(必附)

```markdown
| 項目 | 價格 | 依據 |
|------|------|------|
| 建議進場區間 | $X ~ $Y | {支撐位/均線,引 compute_ta} |
| 止損 (SL) | $Z | {支撐 − n×ATR} |
| 止盈 1 (TP1) | $A | {最近壓力位} |
| 止盈 2 (TP2) | $B | {延伸目標} |
| 風險報酬比 (R:R) | 1 : m | (TP1−進場中點)/(進場中點−SL) |
```

R:R < 1.5 → 表格照給但結論改「建議等待」,並寫明等待條件。

### Q2 — 長期論點區塊

6 個月論點 / 12 個月論點 / 關鍵假設清單 / 合理估值區間與現價位置。

### Q3 — 推薦排序表

```markdown
| 排名 | 標的 | 推薦指數 | 信心 | 進場參考 | 主要風險 |
```

每檔加一段論述;**主要風險欄不得留空**。

### Q4 — 情境樹

突破 / 回踩 / 跌破三情境,各含:觸發條件(具體價位)、機率評估、
對應行動。標注主情境。

### Q5 — 配置對比表

```markdown
| 資產 | 調整前 | 調整後 | 動作 | 理由 |
```

前置:風險承受度/期限/流動性三項確認結果。

## 掛單表區塊(**所有題型必附**,無例外;放在題型專屬區塊之後)

把報告結論轉成可直接執行的限價掛單。**缺掛單表的報告視為未完成**
(與參考資料來源同級的硬性關卡)。

```markdown
## 六、掛單表

| 標的 | 批次 | 掛單價 | 股數/單位 | 金額約 | 依據 |
|------|:---:|-----:|-----:|-----:|------|
| {代號} | 第 1 批 | {價} | {n 股} | {金額} | {支撐/均線/估值區間,引 compute_ta} |
| {代號} | 第 2 批 | {價} | {n 股} | {金額} | {...} |
| {代號} | — | 不掛單 | 0 | 0 | {觀望理由 + 條件單觸發條件} |

**掛單紀律**
1. 取消條件:{收破哪個價位 → 當晚取消所有未成交掛單}(綁定失效條件)
2. {二元事件提醒:horizon 內的財報/法說/除息如何影響掛單}
3. {零股/手續費/ROD 重掛等執行注意事項}
```

規則:

1. **掛單價必須錨定 compute_ta 的支撐/壓力/均線/ATR**(同 rubric §V
   交易計畫規則),禁止憑空給整數關卡;Q2 長期持有錨定合理估值區間下緣。
2. **股數換算的預算來源,依序**:(a) 使用者本次對話提供的金額;
   (b) recall_history / 近期 Q5 配置紀錄中的既有預算框架(沿用時必須
   在表格上方明說「沿用 {日期} 的 {金額} 預算,資金不同請告知重算」);
   (c) 皆無 → 以「每 1 萬元約 n 股」為單位呈現,並提示提供預算可精算。
   **禁止假裝知道使用者資金**。
3. 預設分 2 批(回踩區上緣 + 下緣/次一支撐);單批金額 < 5,000 時
   註明手續費低消侵蝕(零股單筆低消一般 1–20 元,依券商)。
4. **取消條件必填**,直接引用失效條件的價位;失效觸發 = 掛單全撤,
   不是逢低加碼。
5. **結論 = 觀望/等待的標的照樣列入**:掛低接回踩位的被動限價單
   本質就是「等待」,可正常掛;完全不宜進場者寫「不掛單」+ 條件單
   觸發條件(如「放量收上 {壓力} 才試單 {n} 股」)。
   **禁止因為要填表而變相鼓勵追價**;R:R < 1.5 的追價單不得出現在表中。
6. 除息前標的:註明最後買進日,並比較「掛低接單 vs 領息」
   (股息 % vs 折價 %),不得為領息建議改市價追。
7. 賣出/減碼結論 → 掛單表改列賣出限價與分批(錨壓力位),同樣附取消條件。

## 附加區塊(跨題型;依問題內容觸發,附在掛單表區塊之後)

### A. 配息數據區塊(問題提及配息/殖利率/除息/存股領息時**必附**)

```markdown
#### 配息數據({標的})

| 除息日 | 每單位配息 | 當期殖利率 | 填息天數 | 二階段公告日 |
|--------|-----------:|-----------:|---------:|------|
| {YYYY-MM-DD} | {元} | {%} | {n 天 / 尚未填息} | {日期或 —} |
| …近 4 次(季配)或近 3 年(年配)… |

- **配息頻率**:{季配 3/6/9/12 月 / 半年配 / 年配}
- **回顧殖利率(近四季/近一年)**:{%} ｜ **前瞻殖利率(最近一期年化)**:{%,說明推估基礎}
- **下次除息**:預估 {日期}(來源:{官方公告/歷史規律});**參與配息最後買進日 = 除息日前一交易日**
- {ETF 加註}:收益平準金機制下配息可能隨規模變動;成分股股利政策為源頭
- {個股加註}:股利政策(盈餘配發率)、扣抵稅額/二代健保補充保費影響
```

規則:
1. 除息日與配息金額屬**關鍵數字**:官方公告(投信/公司,A 級)優先,
   至少兩來源交叉(rubric §IV);預估值必須標明「預估」與推估方法
2. 回顧 vs 前瞻殖利率**必須分開列**,禁止拿回顧殖利率暗示未來報酬
3. 使用者問「等配息要買多少」→ 在本區塊後接資金試算:
   目標配息金額 ÷ 每單位配息 = 所需單位數,再乘現價得所需資金,
   並提醒**除息日前買進才有配息、貼息風險存在**
4. 本區塊的「下次除息(預估)」與「二階段公告日」屬 Step 5.5 的
   **必記時點**——事件萃取時必須寫入 key_dates(`ex_dividend`,
   預估日標 `estimated`),見「事件萃取規格」規則 3

### B. 比較表格區塊(問題比較 ≥ 2 檔標的時**必附**)

```markdown
#### 標的比較(基準日:{YYYY-MM-DD},所有數字同一基準)

| 指標 | {標的A} | {標的B} | {…} |
|------|--------:|--------:|-----|
| 現價 | | | |
| 推薦指數 / 信心 | | | |
| 回顧殖利率 / 前瞻殖利率 | | | |
| 配息頻率 / 下次除息 | | | |
| YTD / 1 年報酬 | | | |
| 波動(ATR%)/ 距 52 週高 | | | |
| 費用率(ETF)或 PE(個股) | | | |
| 外資近 20 日動向(台股) | | | |
| 主要風險 | | | |
| 適合情境 | {領息/波段/存股…} | | |
```

規則:
1. **同基準日**:每檔都要跑 fetch_ohlcv + compute_ta(台股加 fetch_chips),
   禁止 A 檔用今日、B 檔用上週的數字
2. 「適合情境」是結論欄:比較的答案通常是**情境化建議**
   (短期領息選 X、長期存股選 Y),證據不足以分高下時明說,
   不硬選單一贏家
3. 涉及資金分配(「3 萬怎麼分」)→ 依 Q5 規則補配置對比表,
   並各記一筆預測日誌;純比較(無買賣決策)可只記主要標的一筆

## 事件萃取規格(events.json;SKILL.md Step 5.5)

報告存檔後,把報告內容整理成 payload JSON 存暫存檔,執行
`python log_events.py --file <file>` 合併進 `data/events.json`
(兩區塊文件:`important_events` 重要事件 + `key_dates` 關鍵日期和時間;
腳本以內容雜湊去重,重跑不會重複)。

```json
{
  "report": "2026-07-13_3030-TW_Q1.md",
  "important_events": [
    {"symbol": "3030.TW", "date": "2026-07-10",
     "title": "6 月營收 YoY +0.43%,連三月減速",
     "description": "30%→14.75%→0.43%;失效條件第一隻腳落地",
     "category": "revenue", "impact": "bearish",
     "source_url": "https://mops.twse.com.tw/..."}
  ],
  "key_dates": [
    {"symbol": "3030.TW", "date": "2026-08-10",
     "label": "7 月營收公告截止(基本面證偽觀察點)",
     "date_type": "revenue_release", "status": "estimated",
     "note": "YoY <10% 則題材證偽"},
    {"symbol": "2330.TW", "date": "2026-07-16", "time": "14:00",
     "label": "台積電法說會(牽動設備族群)",
     "date_type": "earnings_call", "status": "confirmed"}
  ]
}
```

規則:

1. **important_events**(已發生/已確認的事實)必填:
   `symbol, date(YYYY-MM-DD), title, category, impact(bullish|bearish|neutral)`;
   選填 `description, source_url` 與任意擴充欄位(會原樣保留)。
   category 建議詞彙:`earnings, revenue, dividend, chips, macro, policy,
   corporate, technical, industry, regulation, other`(可自訂,腳本只警告)。
2. **key_dates**(未來時點)必填:`symbol, date, label, date_type`;
   選填 `time(HH:MM), status(confirmed|estimated,預設 estimated), note`。
   date_type 建議詞彙:`earnings_call, earnings_release, revenue_release,
   ex_dividend, ex_rights, dividend_pay, shareholder_meeting, fed_meeting,
   cpi_release, macro_data, news_release, policy_announcement, lockup_expiry,
   option_expiry, product_launch, horizon_end, other`。
3. **必記時點(報告內文提到就必須進 key_dates,漏記視為 Step 5.5 未完成)**:
   - 除息日/除權日(`ex_dividend`/`ex_rights`)與配息發放日(`dividend_pay`)
     ——配息數據區塊(附加區塊 A)裡的「下次除息」與「二階段公告日」必記
   - 各類**消息/公告的發布日**:財報公布(`earnings_release`)、法說會
     (`earnings_call`)、月營收公告(`revenue_release`)、重大訊息或產品
     發表(`news_release`/`product_launch`)、政策/總經數據發布
     (`policy_announcement`/`fed_meeting`/`cpi_release`/`macro_data`)
   - 失效條件的觀察期限(`horizon_end` 或對應類型)
4. 其餘事件維持挑選標準:**寫進報告論據或失效條件的才記**,不要把整份
   新聞清單倒進去;每份報告通常 1–4 則事件、關鍵日期依必記清單不設上限。
5. 預估日期(如「8/10 前公告」)標 `status: "estimated"` 並在 note 說明;
   只知道月份的用該月最後可能日並在 note 註明推估基礎。
6. `id / logged_at / reports` 由腳本生成,不要手填。

## prediction-meta 規格

單行合法 JSON,藏於 HTML 註解,寫完報告後存檔並執行
`python log_prediction.py --file <file>`。

必填:`asset, asset_type(stock|crypto), question_type(Q1_short_entry|
Q2_long_hold|Q3_screener|Q3_screened_out|Q4_levels|Q5_allocation),
direction(long|short|neutral), recommendation_score(1-100),
confidence_score(1-100), price_at_analysis, horizon_days,
falsification_condition, thesis_summary`

`Q3_screened_out` 是篩選淘汰者的反事實紀錄(見 question-types.md Q3):
照常驗證但不計入勝率/方向準確率統計,僅供漏斗對照。

Q1 的 long/short 必填:`entry_zone([lo,hi]), stop_loss, take_profit([tp1,...])`
(long:SL < entry_lo 且 TP1 > entry_hi;short 相反;腳本會驗證並自動算 R:R)

選填:`timestamp`(省略則以記錄時間為準)。`id / rubric_version / risk_reward`
由腳本自動生成,**不要手填**。

範例:

```json
{"asset":"TSLA","asset_type":"stock","question_type":"Q1_short_entry",
"direction":"long","recommendation_score":72,"confidence_score":65,
"price_at_analysis":245.30,"entry_zone":[240,246],"stop_loss":232,
"take_profit":[260,275],"horizon_days":14,
"falsification_condition":"日線收破 232",
"thesis_summary":"財報催化 + 4H 突破下降趨勢線"}
```
