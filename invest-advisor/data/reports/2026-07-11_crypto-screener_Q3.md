# 【決策報告】加密貨幣短線合約標的篩選 — Q3 標的推薦(Screener)

> 產出時間:2026-07-11T19:15+08:00(UTC 11:15)
> 現價基準:Binance K 線(as_of 2026-07-11T08:00Z)+ 財經媒體交叉確認,詳見「八、參考資料來源」
> 使用者情境:5,000 現金(幣別未確認,以 USDT 假設;若為新台幣約 160 USDT,見「五、合約執行注意事項」)想做短期合約

## 一、結論摘要(TL;DR)

- **建議動作:小倉位、嚴止損的選擇性短多;大盤級別觀望**
- 目前「有」強勢幣,但強勢集中在少數題材(DEXE 治理/AI、ZEC 隱私升級),**不是全面山寨行情**
- BTC 日線與週線仍為下跌趨勢(compute_ta 機械判定),任何多單都是「下跌趨勢中的反彈交易」,倉位必須對應調小
- 推薦排序:**DEXE 72 > ZEC 60 > SOL 53 > ETH 52**(後兩者實為觀望區)
- 一句話理由:資金正選擇性輪動進強動能題材幣,但大盤結構仍空,只適合順動能短打、不適合重倉押方向

## 二、與上次觀點的差異

| 標的 | 上次判斷 | 結果 | 本次立場 |
|------|----------|------|----------|
| DEXE | 首次分析 | — | long 72 |
| ZEC | 首次分析 | — | long 60 |
| SOL | 2026-07-04 long 59/信心 45-50(等回踩 76.7–78 承接) | OPEN,fill 78.0,r=+0.05,方向暫時正確 | **沿用** long 但降至 53:回踩已發生且守住,惟 4h RSI 降至 45、動能未接手,週線仍空 |
| ETH | 2026-07-04 long 55/信心 60(等回踩不追高,PENDING 未進場) | 現價較當時 +1.9% | **修正**為 neutral:新事實 = 價格已直接貼到 $1,800 壓力牆(4h 壓力 1807–1812),而週線 suggested_score 僅 6/100,此位置追多 R:R 不成立 |

- 全系統校準回饋:已判定僅 2 筆(<20),不觸發 rubric §IV 校準調整。

## 三、四維度分析(Q3 權重:消息 30% / 技術 45% / 基本 10% / 宏觀 15%)

### DEXE(DEXEUSDT,現價 $37.00)— 推薦 72 / 信心 70

- **消息面 75**:7/10 突破牛旗創歷史新高 $36.34,單日 +20%;近 24h 清算 96% 為空單(軋空延續);鏈上鯨魚交易、新錢包、活躍地址同創新高。未消化利空:多家分析警告超買回調(coinpedia、crypto.news、ambcrypto)
- **技術面 80**(1d 錨 [80,90],取下緣):1d/4h/1w 三時框同為 uptrend(as_of 7/11),4h 量比 1.36 放量;取區間下緣因 1d RSI14=79.3 過熱、上方無左側壓力參考(價格發現階段)
- **基本面 65**:DeFiLlama TVL ~$1.6B、無合約被駭紀錄、大量供給鎖倉;扣分:YTD +750% 後估值透支基本面
- **宏觀面 45**(封頂):BTC 1d trend=downtrend(benchmark 錨)→ 山寨宏觀上限 45;板塊(AI/治理)資金流入為全場最強

### ZEC(ZECUSDT,現價 $503.8)— 推薦 60 / 信心 60

- **消息面 65**:Ironwood 升級 7/28 啟動(修復 Orchard 反鑄造漏洞+turnstile 強化固定供給)為明確催化;6 月漏洞崩盤(-40~60%)屬已消化利空但信任傷痕仍在
- **技術面 64**(1d 錨 [56,66],取上緣):4h uptrend(84)、1w uptrend(74)支持;1d 為 range、RSI 59.4 健康;量比 0.22 偏低是隱憂
- **基本面 50**:固定供給敘事強化中,但漏洞暴露「靠開發者信任而非密碼學保證」的結構弱點
- **宏觀面 45**(封頂):隱私板塊領漲 7 月反彈,但 BTC 下跌趨勢封頂

### SOL(SOLUSDT,現價 $78.1)— 推薦 53 / 信心 55

- **消息面 58**:Firedancer v1.0 測試網(207 驗證者)、現貨 ETF AUM ~$1B、Morgan Stanley 費率戰 0.14%、Clearstream 機構託管、Alpenglow Q3;負面:ETF 6 月底小幅淨流出、Polymarket 給 7 月觸 $70 機率 52.5%
- **技術面 52**(1d 錨 [50,60];1w 空 vs 1d/4h 中性 → ta-checklist §3 衝突條款壓 40–59):1w downtrend(24/100)、1d range(55)、4h range 且 RSI 45 動能降溫
- **基本面 62**:網路基本面為 L1 中最強(雙客戶端消單點風險、生態輪動有實質資金)
- **宏觀面 43**:Solana 生態是本輪選擇性輪動的受益板塊,但 BTC 下跌趨勢封頂 45 之下再扣大盤 beta

### ETH(ETHUSDT,現價 $1,798)— 推薦 52 / 信心 55

- **消息面 55**:Glamsterdam 升級進入最終開發階段(gas 上限 60M→200M、目標 10k TPS);5 月 ETF 創上市以來最強月流入後,6 月 risk-off 轉弱;現正卡 $1,800 壓力
- **技術面 52**(1d 錨 [50,60];1w 空 vs 4h 偏多 → 衝突條款壓 40–59):1w suggested_score 僅 6/100(深度空頭),1d range,4h 61 偏多但貼壓力
- **基本面 60**:最大智能合約鏈、升級路線明確;H1 明顯跑輸
- **宏觀面 38**:BTC 下跌趨勢 + ETH ETF 流量 6 月轉弱

## 四、多空對辯(市場級)

### 多頭最強論點 ×3

1. **BTC 已收上趨勢轉折參考位**:自 6/26 低點 $57.8K 反彈至 $64.2K,站上 crypto.news 提出的 $63,800(收上此位被視為下跌趨勢可能結束);恐懼貪婪自 7/1 的 11 回升至 19,恐慌高峰或已過(crypto.news、alternative.me)
2. **資金輪動有實據**:BTC.D 自高點回落、山寨市占(除 BTC/ETH/穩定幣)19.4%→24.7%,DEXE、ZEC、ADA 領漲,選擇性山寨行情已在進行(cryptorank、coinmarketcap)
3. **宏觀順風出現**:7/3 非農弱於預期 → Fed 寬鬆預期升溫,高 beta 風險資產受益(crypto.news)

### 空頭最強論點 ×3(聰明空頭視角)

1. **趨勢結構仍空(機械錨)**:BTC 1d 與 1w 皆 downtrend(compute_ta as_of 7/11),SMA200($74K)遠在現價之上;6 月 BTC ETF 淨流出 $4.5B 創紀錄、Citi 下修 12 個月目標至 $82K 並示警最壞 $53K——這只是下跌趨勢中的反彈(Yahoo Finance、Citi via Yahoo)
2. **「強勢」全靠槓桿與軋空**:山寨季指數 46 仍屬比特幣季;DEXE 日線 RSI 79(有分析引 RSI 87)極度超買、ZEC 期貨量 $1.35B 是現貨 $115M 的 12 倍、OI $798M 擁擠——槓桿驅動的上漲回撤時跌更快(bitget、FXEmpire、cryptonews)
3. **事件風險在前**:7/28–29 FOMC,Warsh 不預告政策路徑;ZEC Ironwood 若再延期即重挫;Polymarket 給 SOL 7 月觸 $70 機率 52.5%(crypto.news、bitcoinfoundation)

### 裁決

**空方整體證據較強**(大盤趨勢結構 + 流動性數據都站在空方),多方優勢僅存在於「局部強動能標的」。因此本報告不做大盤級看多,只給**順動能、小倉位、嚴止損**的選擇性短多;推薦指數最高僅 72、SOL/ETH 落中性觀望區——與裁決方向一致。

## 五、Q3 推薦排序表 + 合約執行注意事項

| 排名 | 標的 | 推薦指數 | 信心 | 方向 | 進場參考 | 主要風險 |
|:---:|------|:---:|:---:|:---:|----------|----------|
| 1 | DEXE | 72 | 70 | long | **勿追價**。回踩 $30–32(4h 支撐 29.88 + 4h SMA20 32.0)承接;SL $28.2(支撐下方 0.5×1d ATR);TP1 $37.6(前高)/ TP2 ~$44(+2×ATR);R:R ≈ 2.4 | 1d RSI 79 極度超買;軋空動能一旦耗盡,價格發現段的回撤常達 20–40%;1d ATR 9% 高波動 |
| 2 | ZEC | 60 | 60 | long | 回踩 $482–490(1d 支撐群 482–487)承接;SL $462(482 − 0.5×ATR);TP1 $530 / TP2 $560(1d 壓力);R:R ≈ 1.7 | Ironwood(7/28)延期或出包 → 直接跌 30% 級別;OI 擁擠、期現量比 12:1,雙向清算風險大 |
| 3 | SOL | 53 | 55 | long(僅觀察) | **現位不進**(TP1 78.4 太近,R:R < 1)。二擇一:日線收復 $80 後順勢追;或回踩 $76.7(週線支撐)守住再接,SL $74.9 | 週線仍為下跌趨勢;Polymarket 7 月觸 $70 機率 52.5%;跌破 76.7 直接看 $70/67.5 |
| 4 | ETH | 52 | 55 | neutral | **現位不進**。收上 $1,812(4h 壓力上緣)站穩才追多;或 $1,716–1,748 承接(1d 支撐 1747.8 + 日線 S1 1716) | 週線深度空頭(suggested 6/100);日線收破 $1,716 整體轉空;$1,800 是三度測試的壓力牆 |

**淘汰紀錄(反事實)**:TRX(61,ATR 1.45% 波動不足不適合短線合約)、ONDO(47)、LINK(40)、ADA(32,上週 +26% 動能已退且仍處日線下跌趨勢)、BNB(32)、XRP(32)。HYPE 因 Binance 無現貨資料源被剔除(未評分)。

### 合約執行注意事項(針對 5,000 資金)

1. **幣別確認**:若 5,000 = USDT,單筆風險上限 1–2%(50–100 USDT 虧損額),對應上表 SL 距離反推倉位;若 5,000 = 新台幣(≈160 USDT),**誠實建議:不要做合約**——手續費+資金費率會吃掉小資金的期望值,現貨定期定額更合理
2. **槓桿 ≤ 3x,新手建議 1–2x**:上表標的 1d ATR 在 3–9%,3x 槓桿下單日正常波動即 ±9–27%,10x 以上等於把 SL 交給清算引擎
3. **資金費率**:本次未能取得各標的即時資金費率(單一來源亦缺),進場前務必在交易所確認——強勢幣軋空段的正費率常態性偏高,持多過夜成本不可忽略
4. 一次最多持有 1–2 個標的的倉位;DEXE 與 ZEC 同屬「高動能高波動」桶,兩者同時滿倉等於變相加槓桿

## 六、失效條件(可證偽)

- **市場級**:BTC 日線收破 $62,272(1d 第三支撐)→ 反彈論證失效,所有多單離場觀望
- DEXE:日線收破 $29.88(4h 結構支撐)→ 動能結束
- ZEC:日線收破 $482.2,或 Ironwood 官方宣布再度延期
- SOL:日線收破 $76.7(週線支撐)
- ETH:日線收破 $1,716(cryptonomist 日線 S1,與 1d 支撐 1747 群下緣一致)

## 七、風險聲明

本報告為 AI 綜合公開資訊之分析,**非投資建議**;資料可能延遲(K 線 as_of 2026-07-11T08:00Z,較產出時間舊約 3 小時)或有誤,最終決策與風險由使用者自行承擔。合約交易含槓桿與清算機制,虧損可能超過本金承受範圍;DEXE/ZEC 之上漲高度依賴槓桿資金,回撤速度可能遠快於上漲。分數是公開資訊的結構化綜合,不是 alpha 保證。

## 八、參考資料來源

### 網路來源(查詢日期均為 2026-07-11)

| 來源 | URL | 支持論點 |
|------|-----|----------|
| crypto.news(BTC 7 月展望/Fed) | https://crypto.news/bitcoin-price-prediction-july-2026-fed-decides/ | BTC $63,800 轉折參考位、FOMC 事件風險 |
| Yahoo Finance(BTC ETF 最差月) | https://finance.yahoo.com/markets/crypto/articles/bitcoin-price-prediction-july-2026-081429814.html | 6 月 ETF 流出 $4.5B、$42K 風險論 |
| BeInCrypto(7 月第二週強勢幣) | https://beincrypto.com/crypto-altcoins-to-watch-july-second-week-2026/ | DEXE/LIT/ADA 為週漲幅榜首 |
| BeInCrypto(7 月五大催化幣) | https://beincrypto.com/top-5-altcoins-to-watch-july-2026/ | SOL/HYPE/ZEC/ONDO/TRX 催化清單 |
| CryptoRank(BTC.D 輪動) | https://cryptorank.io/news/feed/6227b-bitcoin-dominance-altcoin-market-rotation | 山寨市占 19.4%→24.7% |
| TradingView Hub(BTC.D) | https://www.tv-hub.org/guide/bitcoin-dominance | BTC.D ~58% |
| Bitget(山寨季指數) | https://www.bitget.com/price/altcoin-season-index | 指數 46,仍屬比特幣季 |
| Alternative.me(恐懼貪婪) | https://alternative.me/crypto/fear-and-greed-index/ | F&G 19,自 11 回升 |
| Coinpedia(DEXE ATH) | https://coinpedia.org/price-analysis/dexe-price-hits-new-all-time-high-after-changenow-listing-boost/ | DEXE ATH $36.34 |
| crypto.news(DEXE 上漲原因) | https://crypto.news/heres-why-dexe-price-is-rallying/ | 軋空 96%、TVL $1.6B、鏈上活躍創高 |
| AMBCrypto(DEXE 空方) | https://ambcrypto.com/dexe-price-prediction-can-bulls-take-back-15-40-after-a-7-5-drop/ | 超買回調警告 |
| CryptoBriefing(Ironwood 7/28) | https://cryptobriefing.com/zcash-ironwood-upgrade-fake-zec/ | ZEC 升級日期與內容 |
| CoinDesk(ZEC Orchard 漏洞) | https://www.coindesk.com/markets/2026/06/05/zcash-plummets-30-as-developer-reveals-a-major-bug-that-went-undetected-for-four-years | 6 月崩盤背景 |
| FXEmpire(ZEC 空方) | https://www.fxempire.com/forecasts/article/zcash-zec-price-risks-30-drop-amid-41m-long-liquidation-threat-1608937 | $41M 清算威脅、30% 回落風險 |
| The Crypto Times(ZEC $500) | https://www.cryptotimes.io/2026/07/09/zcash-zec-rockets-past-500-on-ironwood-upgrade-momentum-whats-next/ | ZEC 站回 $500 |
| BeInCrypto(SOL 7 月展望) | https://beincrypto.com/what-to-expect-from-solana-sol-in-july-2026/ | Firedancer/ETF/Alpenglow 催化 |
| Bitcoin Foundation(7 月風險總覽) | https://bitcoinfoundation.org/news/altcoins/top-july-2026-crypto-updates-is-crypto-crash-coming/ | Polymarket SOL $70 機率 52.5%、空方總論 |
| CoinDesk(Glamsterdam) | https://www.coindesk.com/tech/2026/06/16/ethereum-s-biggest-protocol-overhaul-in-years-moves-into-its-final-development-stage | ETH 升級進最終開發階段 |
| Cryptonomist(ETH 空方) | https://en.cryptonomist.ch/2026/07/08/ethereum-price-analysis-bearish-july-2026/ | $1,716 關鍵支撐、日線轉空條件 |

### 本地資料

- market.db / compute_ta.py:BTCUSDT、DEXEUSDT、ZECUSDT、SOLUSDT、ETHUSDT + 6 檔淘汰者,1d/4h/1w,as_of 2026-07-11T08:00Z(1d 為 00:00Z),stale_bars 全部 0
- cache_news.py --recall:4 檔命中 0 筆(本次新聞已回寫快取 5 筆)
- recall_history.py:SOL 2 筆(OPEN/PENDING)、ETH 1 筆(PENDING)、DEXE/ZEC 0 筆

### 現價來源(雙來源)

Binance K 線(market.db,2026-07-11T08:00Z)× 財經媒體報價交叉:DEXE $37.0 vs 媒體 ATH $36.34(7/10);ZEC $503.8 vs 媒體「站回 $500」(7/9-10);SOL $78.1 vs 媒體 $77–78(7/8-11);ETH $1,798 vs 媒體「$1,800 壓力」(7/9);BTC $64,196 vs 媒體「低 $60K 區」。一致。

<!-- prediction-meta: 本報告為 Q3 篩選,共 10 筆預測(4 檔入選 Q3_screener + 6 檔淘汰 Q3_screened_out),已逐筆經 log_prediction.py 寫入 predictions.jsonl,meta JSON 見 scratchpad 存檔 -->
