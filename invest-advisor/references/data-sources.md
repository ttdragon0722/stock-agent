# 資料來源優先序與抓取策略

## 1. 分層與 TTL(Freshness Gate)

| 資料類型 | 存本地? | TTL | 過期處理 |
|---------|:---:|------|------|
| 即時價格、盤中新聞 | ❌ 永遠現抓 | — | 報告標註查詢時間戳 |
| 新聞情緒摘要 | news_cache.db | 24h | 過期即現抓,cache_gc 清除 |
| 歷史 OHLCV | market.db | 永久(歷史不變) | 增量更新(fetch_ohlcv.py) |
| 台股籌碼(法人/融資券) | market.db chips 表 | 永久(歷史不變) | 增量更新(fetch_chips.py) |
| 官方公告/月營收 | ❌ 永遠現抓(fetch_mops.py) | — | 報告標註查詢時間戳 |
| 基本面(財報等) | fundamentals 表 | 至下次財報日 | 過期即現抓 |
| 標的靜態檔案 | asset_profiles 表 | 30d | cache_gc 清除 |
| 預測日誌 / 判定結果 | predictions.jsonl / outcomes.jsonl | 永久 | append-only / 每次重建 |

> RAG 不會自動降低幻覺——帶著過時資料的檢索會產生「有憑有據的錯誤」。
> 即時性資料寧可不存;凡引用本地資料,報告必須標註資料時間(as_of)。

## 2. OHLCV 來源

| 資產 | 來源 | 時框 | 備註 |
|------|------|------|------|
| 加密貨幣 | Binance 公開 REST | 1d / 4h / 1w | 免 key,自動轉 USDT 對 |
| 股票 | Yahoo Finance v8 chart API | 1d / 1w | 免 key;**無 4h**(免費源皆無可靠盤中歷史) |

- ~~Stooq~~ 已棄用:2026-07 起有 JavaScript 驗證牆,腳本無法通過
- Yahoo 端點若失效:備援選項為安裝 yfinance(pip)或改用 Alpha Vantage
  (需免費 key),屆時修改 fetch_ohlcv.py 並記錄於本文件
- 台股/其他市場:Yahoo 符號格式(如 `2330.TW`)直接可用

## 2.5 台股官方數據(fetch_chips.py / fetch_mops.py,A 級來源)

| 資料 | 端點 | 涵蓋 |
|------|------|------|
| 三大法人買賣超 | TWSE rwd T86(上市,可逐日回補)/ TPEx OpenAPI(上櫃,僅最新日) | 個股,單位:股 |
| 融資融券 | TWSE rwd MI_MARGN(僅上市) | 個股餘額與增減,單位:張 |
| 重大訊息/月營收 | TWSE OpenAPI t187ap04/05_L(上市)、TPEx mopsfin_..._O(上櫃) | 近期公告 |

- 全部免 key;TWSE rwd 端點有速率限制,腳本已內建 2 秒間隔,
  **不得**繞過腳本直接高頻呼叫
- 上櫃限制:無融資融券、法人數據無歷史回補(靠每次執行累積入庫)
- TPEx 憑證缺 SKI,腳本已放寬 Python 3.13 strict flag(鏈仍完整驗證)
- 已知限制:OpenAPI 重大訊息僅含近期資料,「查無公告」不代表期間內
  無公告,報告不得反向推論

## 3. 現價與新聞(WebSearch)

- 現價:搜尋後取兩個獨立來源交叉確認;差異 > 1% 時標註兩者與出處
- 新聞:近 7 天為主;每標的 3–8 次搜尋,涵蓋
  ①公司/項目新聞 ②財報/公告 ③監管/宏觀 ④(幣)鏈上與衍生品數據
- **反向查詢(強制)**:每標的至少 1 次搜尋必須找反面證據
  (「{標的} 利空/風險/做空理由」),結果餵入 Step 3.5 空頭論點
- **快取流程(強制,經 cache_news.py,禁止手寫 SQL)**:
  1. 搜尋前 `python cache_news.py --recall <symbol>` 取未過期摘要
     (ETF 標的改用 `--recall <symbol> --with-proxies`,見 §3.1)
  2. 搜尋後把每則摘要(symbol/headline/summary/sentiment/source_url,
     sentiment 限 positive|negative|neutral|mixed)存成 JSON 陣列檔,
     `python cache_news.py --save <items.json>` 入庫(24h TTL,自動去重)
  3. 存檔後跑 `python cache_news.py --stats --symbol <symbol>` 檢查來源
     多樣性,`flags` 與 `confidence_penalty` 直接寫入報告(見 §4.1)

## 3.1 ETF 代理來源(強制,scripts/etf_proxies.py)

ETF 沒有個股層級新聞,只搜到大盤通稿時,消息面等於沒有可歸因的證據。
**分析 ETF 時必須一併蒐集代理標的(權重最大成分股 + 對應指數)的新聞**:

| ETF 類型 | 代理標的 | 例 |
|------|------|------|
| 市值型(台灣 50/TOP50) | 台積電、鴻海 + ^TWII | 0050、009816、006208 |
| 高股息型 | 主要成分金融/電子 + ^TWII | 0056、00918、00919、00878 |
| 海外科技型 | NVDA、MSFT + SPY | 009824、00980A |

- 對照表在 `scripts/etf_proxies.py` 的 `PROXY_MAP`,未收錄的台股 ETF
  預設代理 `^TWII`;新增 ETF 時同步更新該表與本節
- `python cache_news.py --recall 0050.TW --with-proxies` 會回傳
  ETF 自身與各代理標的的快取新聞
- 代理標的的新聞**計入獨立來源數**,但報告必須標明
  「本論據來自代理標的 2330.TW,非 0050 本身」,不得偽裝成 ETF 的個股消息
- ETF 專屬的一手來源(A 級):發行商官網月報/持股、TWSE 淨值與折溢價

## 4. 交叉驗證規則(含獨立來源計數)

- 關鍵數字(現價、財報數據、代幣解鎖量)至少 2 個獨立來源
- 本地快取只計為一個來源;第二來源必須是當次現抓
- 衝突處理:報告並列兩個數字與出處,採用較保守者計算交易計畫,
  並在信心指數扣分(rubric §IV)

## 4.1 獨立來源計數(強制,cache_news.py --stats)

「幾則新聞」不是資訊量,「幾個獨立來源」才是。同一則通稿被
udn / ETtoday / 中時同時轉載,在快取裡是 3 列、在判斷上是 1 個來源。

- 計數由 `python cache_news.py --stats [--symbol X]` 產出,**禁止目測**。
  規則實作於 `scripts/source_audit.py`:以註冊網域去重,
  同集團網域(ctee↔chinatimes、money.udn↔udn、Yahoo 各頻道)併為一個
- 報告的「參考資料來源」節必須寫出 **獨立來源 N 個(去重後)**,
  而不是只列則數
- `flags` 對應處置:

| flag | 意義 | 處置 |
|------|------|------|
| `weak_source_count` | 獨立來源 < 3 | 信心 −10,報告明說資料稀缺(rubric §IV) |
| `single_domain_dominant` | 單一網域 > 60% 且 ≥ 4 則 | 信心 −5,多空對辯須註明敘事可能單邊 |
| `no_foreign_source` | 無外媒對照 | 權值股/國際標的必須補一次英文搜尋;補不到則在報告註明 |
| `no_primary_source` | 快取內無一手來源 | 提示性質,不重複扣分(A 級數據另由 fetch_chips/fetch_mops 供應) |

- `confidence_penalty` 是建議扣分(≤ 0),與 rubric §IV 其他條款相加後
  一併計入信心指數,報告須寫出扣分明細

## 5. 抓取失敗的降級路徑

1. fetch_ohlcv 失敗 → 重試一次 → 仍失敗則改用 WebSearch 找現價與
   近期高低點,技術面分數上限 59(無確定性指標),信心 −10 並註明
2. 冷門標的 `independent_sources` < 3(去重後,ETF 併計代理標的)
   → 信心 −10,報告明說資料稀缺;僅則數多但來源集中同樣算稀缺
3. Binance 無該交易對 → 嘗試其他計價對(BUSD 已退場,試 FDUSD/BTC 對)
   或改以 CoinGecko 頁面數據 + 上限 59 的技術面處理
4. fetch_chips / fetch_mops 失敗 → 重試一次 → 仍失敗則台股分析照常進行,
   但報告註明「籌碼面/官方公告不可用」;若新聞中的籌碼敘事無官方數據
   可驗證,該論據降為 B 級且信心 −5
