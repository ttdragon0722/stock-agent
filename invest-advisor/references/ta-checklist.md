# 技術分析檢查表

> **鐵律:所有指標數值必須來自 `compute_ta.py` 輸出。**
> LLM 不得目測 K 線、心算指標、或從網頁文章抄指標數值——那是幻覺重災區。
> 網路來源的技術觀點只能作為「他人觀點」引用,不得當作指標事實。

## 1. 執行順序

```bash
python fetch_ohlcv.py --symbol <SYM>,<BENCH> --asset-type <type> --timeframe 1d
python fetch_ohlcv.py --symbol <SYM> --asset-type <type> --timeframe 1w
python compute_ta.py --symbol <SYM> --timeframe 1d
python compute_ta.py --symbol <SYM> --timeframe 1w
# 加密貨幣加做: --timeframe 4h(股票無 4h,見 data-sources.md)
```

執行前檢查:`stale_bars > 3` 或 stderr 有 WARN → 先重跑 fetch 再算。

## 2. 輸出欄位解讀

| 欄位 | 用途 | 判讀 |
|------|------|------|
| `trend` | 趨勢結構(價格 vs SMA20/50/200) | uptrend / downtrend / range |
| `sma20/50/200` | 均線排列與動態支撐壓力 | 多頭排列 = close > 20 > 50 > 200 |
| `rsi14` | 動能 | 50–70 健康多頭;>70 過熱;<30 超賣;40–60 中性 |
| `macd.cross` | 動能轉折 | bullish/bearish = 本根柱狀圖翻正/翻負 |
| `macd.hist` | 動能強度變化 | 連續縮短 = 動能衰竭前兆 |
| `atr14` / `atr_pct` | 波動度 | SL 距離與倉位參考;atr_pct > 5% = 高波動標的 |
| `supports` / `resistances` | 擺動樞紐位(距現價最近的 3 個) | 進場/SL/TP 錨點 |
| `high_52w` / `dist_52w_high_pct` | 相對位置 | 接近 52w 高 = 動能強但追高風險 |
| `vol_ratio_20` | 量能 | >1.5 放量;<0.7 量縮(突破無量 = 存疑) |

## 3. 多時框合成

- 1w 定方向、1d 定結構、4h(僅加密貨幣)定進出場
- 時框衝突(1w 空、1d 多)→ 技術面分數壓在 40–59,信心指數 −15
  (scoring-rubric §IV 訊號矛盾條款)
- 只有主時框一致 + 動能確認才允許技術面 ≥ 80

## 4. 交易計畫錨定規則

- 進場區間:最近支撐上緣 ~ 現價之間,或突破回踩位
- SL:關鍵支撐下方 0.5–1.0 × `atr14`(short 相反)
- TP1:`resistances[0]`;TP2:`resistances[1]` 或量測目標
- 支撐壓力清單為空(歷史新高的標的)→ 用 ATR 倍數建構目標,
  並在報告註明「無左側參考位」

## 5. 常見型態的證據標準

型態判讀(頭肩、旗形、雙底等)允許以 supports/resistances +
趨勢欄位推論,但必須寫明推論依據(哪兩個樞紐位構成頸線),
且型態只能作為輔助證據,不得單獨支撐 80+ 的技術面分數。
