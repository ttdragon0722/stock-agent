# invest-advisor Dashboard(Web 版)

前後端分離的預測總覽網頁:**FastAPI 後端**以 API 提供 skill 資料層的內容,
**Next.js 前端**呈現。skill 仍是唯一的資料寫入者;本服務對
`predictions.jsonl` 只讀不寫。

```
dashboard/
├── start.ps1            # 一鍵啟動前後端 + 開瀏覽器
├── backend/
│   ├── main.py          # FastAPI(直接 import skill 的 scripts/ 模組,單一事實來源)
│   ├── test_api.py      # TestClient API 測試
│   └── requirements.txt
└── frontend/            # Next.js 16(App Router + TypeScript + Tailwind v4)
    └── src/
        ├── lib/types.ts        # API 契約型別(與後端回應一一對應)
        ├── lib/api.ts          # 帶型別的 fetch 層(NEXT_PUBLIC_API_URL 可換環境)
        ├── components/         # StatsCards / PredictionsTable / ReportsPanel
        └── app/page.tsx        # 儀表板主頁
```

## 啟動

```powershell
cd D:\coding\stock-agent\dashboard
.\start.ps1        # 開兩個視窗(uvicorn :8787 / next dev :3000)+ 自動開瀏覽器
```

或手動:

```bash
cd backend  && python -m uvicorn main:app --reload --port 8787
cd frontend && npm run dev        # http://localhost:3000
```

## API 一覽(Swagger:http://localhost:8787/docs)

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/health` | 健康檢查 + 資料目錄位置 |
| GET | `/api/predictions` | 預測日誌(已 join 判定結果、到期倒數、可驗證旗標) |
| GET | `/api/stats` | 勝率 / 期望值(R)/ 方向準確率 / 超額報酬 |
| GET | `/api/reports` | 決策報告清單 |
| GET | `/api/reports/{name}` | 單份報告 markdown(有路徑遍歷防護) |
| GET | `/api/calibration` | 信心校準表 + Brier + 單調性 + regime 分層 |
| POST | `/api/verify?fetch=true` | 執行驗證(先自動更新 K 線),回傳統計摘要 |

回應一律使用 `{ success, data, error, meta? }` envelope。

## 前端功能

- 統計卡片(勝率、期望值、方向準確率、平均超額報酬,樣本不足警語)
- 預測總表:狀態彩色標籤、到期倒數、「可驗證」提醒橫幅
- 「🔄 執行驗證」按鈕 → 呼叫 `/api/verify` → 自動刷新全部資料
- 決策報告瀏覽器(markdown 渲染,含 GFM 表格)

## 擴充指引

- **加後端端點**:在 `backend/main.py` 新增 route,邏輯盡量放回 skill 的
  `scripts/` 模組再 import(維持單一事實來源),並在 `test_api.py` 補測試。
- **加前端區塊**:`lib/types.ts` 補型別 → `lib/api.ts` 補 fetcher →
  `components/` 新元件 → `page.tsx` 組裝。
- **改 API 位址/部署**:前端只依賴 `NEXT_PUBLIC_API_URL`(`.env.local`);
  後端 CORS 允許清單在 `main.py` 頂部。
- 舊的靜態版 `invest-advisor/scripts/dashboard.py` 保留為零依賴備援
  (產生單檔 HTML,不需要 Node)。
