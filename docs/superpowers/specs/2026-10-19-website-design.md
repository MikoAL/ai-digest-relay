# AI 每日研究摘要網站 — 規格書

日期：2026-10-19
作品：`ai-digest-relay` repo 根目錄的單一 `index.html`，透過 GitHub Pages 公開於 `https://mikoal.github.io/ai-digest-relay/`

## 1. 目標

一個打開就能看「今天 AI 研究新聞」的網站。資料來自本 repo 每天 09:20（台北時間）由排程寫入的 `digests/`，網站只負責讀取與呈現，讓使用者可以快速瀏覽、篩選、深入閱讀每一則摘要，並回顧過去的日期。

**成功標準**
- 打開網址即顯示最新一天的摘要，不需任何操作。
- 排程寫入新的一天後，重新整理網頁就會出現，不需要修改網頁本身。
- 下列第 4 節的每一項互動都能實際操作。
- 在桌機與手機寬度（≥ 360px）都能正常使用，無橫向捲動。

## 2. 限制

- 單一 `index.html`，CSS 與 JavaScript 直接寫在檔案內；不使用外部函式庫、外部字型或 build 步驟。
- 依 README 規定：網站只能**讀取** `digests/index.json` 與 `digests/YYYY-MM-DD.json`，不得修改 `digests/` 與 `scripts/` 底下任何檔案。
- 靜態網站無法列出資料夾，日期清單一律從 `digests/index.json` 取得。
- 介面文字使用繁體中文；摘要內容維持資料中的英文原文。

## 3. 資料來源（既有資料格式，schema_version 1）

- `digests/index.json`：`digests[]` 由新到舊，每筆含 `date`、`item_count`、`on_focus_count`、`top_headline`、`json`（該日 JSON 路徑）。
- `digests/YYYY-MM-DD.json`：含 `date`、`generated_at`、選填 `notes`、`items[]`。
- 每則 item：`id`、`kind`（paper / news / release）、`title`、`url`、`source`、`category`（architecture / efficiency / scaling / training / inference / other）、`on_focus`、`headline`、`summary`、`result`（選填）、`critique`、`authors`（選填）、`arxiv_id`（選填）。

網站遇到 `schema_version` 不是 1 時，仍嘗試顯示，並在頁面上方提示「資料格式版本不同，部分內容可能無法正確顯示」。

## 4. 功能

### 4.1 看今天（預設畫面）
- 載入時讀 `index.json`，預設選取最新一天（`digests[0]`），再讀取該日 JSON。
- 條目標題旁標示狀態：該日等於台北今天的日期 →「今天」；是最新一天但不是今天 →「最新」；其他 →「歷史」。
- 台北今天的日期以 `Intl.DateTimeFormat`（`timeZone: 'Asia/Taipei'`）計算。

### 4.2 切換日期
- 左側欄列出 `index.json` 內所有日期（含每日則數），目前日期以粗體、非連結呈現。
- 條目上方有「← 前一天」「後一天 →」，到盡頭時呈灰色不可點。
- 選取的日期寫入網址 hash（例如 `#2026-10-18`），可分享連結；瀏覽器上一頁／下一頁可切換日期。
- hash 指向不存在的日期時，顯示提示並改顯示最新一天。

### 4.3 篩選
位於右側資訊框下方的「篩選」方框，全部可同時套用（AND）：
- 類型：paper / news / release 核取方塊（預設全選）。
- 分類：六種分類核取方塊（預設全選；只列出當天有出現的分類，並顯示數量）。
- 「只看 on-focus」「只看收藏」「隱藏已讀」三個開關。
- 顯示「顯示 x / y 則」，以及「清除篩選」連結。
- 篩選設定在切換日期時保留。

### 4.4 關鍵字搜尋
- 頁首搜尋框，即時篩選當天各則。
- 比對欄位：title、headline、summary、result、critique、authors、source、arxiv_id；不分大小寫，以空白分隔多個關鍵字，全部都要符合。
- 符合的文字以醒目底色標示。
- 搜尋範圍為目前顯示的日期。

### 4.5 展開／收合
- 每則預設收合，只顯示章節標題（headline）與一行中繼資訊（類型、分類、來源、on-focus 標記）。
- 點章節標題展開，依序顯示小節：「摘要」（summary）、「結果」（result，有才顯示）、「評析」（critique），以及作者、arXiv ID、原文連結。
- 頁面上方有「全部展開／全部收合」。
- 目錄（Contents）列出當天所有 headline，點擊會跳到該則並自動展開。

### 4.6 已讀與收藏
- 每則章節標題旁有 `[原文]` `[☆ 收藏]` `[✓ 已讀]` 連結，模仿 Wikipedia 的 `[編輯]`。
- 展開某則時自動標為已讀，也可手動切換。已讀的章節標題顏色變淡。
- 以 `日期/id` 為 key 存在 localStorage；所有讀寫都包在 try/catch 內，無法使用 localStorage 時功能退化為僅在本次瀏覽有效，頁面照常運作。

### 4.7 深色模式
- 預設跟隨系統（`prefers-color-scheme`）。
- 頁首有切換鈕，循環「自動 → 淺色 → 深色」，選擇存在 localStorage。

## 5. 視覺：Wikipedia 風格（參考 Vector 2022）

- 白底、細灰框線、幾乎無陰影與圓角，閱讀感像百科條目。
- 字體：標題用襯線 `'Linux Libertine','Georgia','Times',serif`（中文 fallback 系統明體）；內文用系統無襯線字體。
- 色彩（淺色）：連結 `#3366cc`、已造訪連結 `#6b4ba1`、框線 `#a2a9b1`、次要底色 `#f8f9fa`、文字 `#202122`。深色模式參考 Wikipedia 夜間模式（底 `#101418`、文字 `#eaecf0`、連結 `#88a3e8`）。

**版面**
| 區塊 | 內容 |
|---|---|
| 頁首 | 左：網站名稱「AI 研究日報」與 tagline「自由的每日 AI 研究文摘」；右：搜尋框、深色模式切換 |
| 左側欄 | 「日期」導覽清單、「關於」連結（GitHub repo） |
| 條目主體 | 襯線大標題（例如「2026年10月19日」＋狀態標籤）與底線；`notes` 以灰框 hatnote 呈現（過長時可收合）；目錄；各則章節 |
| 右側資訊框 | 則數、on-focus 數、各分類則數、產生時間（台北時間）；下方為篩選方框 |
| 頁尾 | 「本頁資料最後更新於 …」、資料來源說明、GitHub 連結 |

**手機版（寬度 < 800px）**：左側欄改為頁首下方的日期下拉選單；資訊框與篩選移到標題下方；左右 16px 邊距。

## 6. 錯誤與空狀態

- `index.json` 或當日 JSON 讀取失敗：條目區顯示錯誤訊息與「重試」按鈕。
- 以 `file://` 直接開啟（瀏覽器會擋 fetch）：額外提示「請透過 GitHub Pages 或本機伺服器（`python3 -m http.server`）開啟」。
- 尚無任何 digest：顯示「目前還沒有任何摘要」。
- 篩選／搜尋後沒有結果：顯示「沒有符合條件的項目」與「清除篩選」。
- 所有 fetch 使用 `cache: 'no-cache'`，排程更新後重新整理即可看到新資料。
- 資料中的文字一律以 `textContent` 插入，不使用 `innerHTML` 插入資料，避免注入。

## 7. 檔案異動

- 新增 `index.html`（整個網站）。
- 新增 `.nojekyll`（讓 GitHub Pages 原樣提供檔案）。
- 修改 `README.md` 的 Website 段落，說明網址與本機預覽方式。
- 不修改 `digests/`、`scripts/`。

## 8. 驗證

- 以 `python3 -m http.server` 本機開啟，用瀏覽器逐項操作第 4 節所有功能，並測試手機寬度與深色模式。
- 執行 `python3 scripts/publish.py --check`，確認輸出 `OK`。
- 推上 GitHub 並開啟 Pages（main 分支、根目錄）後，以實際網址再檢查一次並截圖。
