# Game_Radar

**遊戲資料收集與追蹤 API 專案**

Game_Radar 是一個用來收集、追蹤、整理遊戲資料的後端 API 專案。
目前主要用途如下：

* 串接外部遊戲資料來源
* 建立與管理 tracker（追蹤器）
* 依條件手動或批次執行資料抓取
* 將資料寫入資料庫
* 提供 API 給未來的網站前端專案使用

> 未來網站專案會另外開發，但會直接使用本專案提供的 API 與資料。

---

# 目前已完成的功能

* Tracker 建立 / 修改 / 刪除 / 查詢
* 單筆 tracker 手動執行
* 依 `update_frequency` 批次執行 tracker
* `mock` 與 `rawg` 雙資料來源
* `runs` 執行紀錄
* `games` 遊戲資料查詢
* APScheduler 自動排程執行
* `latest_update_date` 欄位打通
* `query_json` 新格式驗證
* Dashboard API（summary / recent-runs / recent-games / active-trackers）
* Scheduler 狀態查詢 API
* `unittest` API 測試
* GitHub Actions 自動測試流程
* Docker / Docker Compose 啟動流程

---

# 專案定位

本專案的角色是：

> **遊戲資料收集與追蹤 API 服務**

此專案負責：

* 收集遊戲資料
* 整理與儲存資料
* 建立追蹤條件
* 執行追蹤
* 提供查詢 API

此專案**不負責**：

* 前端頁面
* 使用者評論 UI
* 評分 UI
* 使用者登入介面

---

# 專案使用到的套件

以下是目前程式中實際有用到的主要套件，以及它們在本專案中的用途。

## 1. FastAPI

### 用途

FastAPI 是本專案的 API 框架，用來建立後端服務與定義各種路由。

### 在本專案中的使用

* 建立 `/health`
* 建立 `/v1/trackers`
* 建立 `/v1/games`
* 建立 `/v1/runs`
* 建立 dashboard API
* 建立 scheduler status API
* 建立批次執行 API

### 常見寫法

```python
from fastapi import FastAPI, Depends, HTTPException

app = FastAPI(title="Game Radar", version="0.1.0")
```

---

## 2. Uvicorn

### 用途

Uvicorn 是 FastAPI 的 ASGI Server，用來啟動 API 服務。

### 在本專案中的使用

* 本機開發時啟動伺服器
* 使用 `--reload` 自動重啟，方便開發

### 啟動方式

```bash
python -m uvicorn app.main:app --reload
```

---

## 3. SQLAlchemy

### 用途

SQLAlchemy 是 ORM（Object Relational Mapper），讓我們可以用 Python 操作資料庫，而不用一直手寫 SQL。

### 在本專案中的使用

* 定義資料表模型
* 查詢 tracker / game / run
* 寫入與更新資料
* 建立 `Tracker`、`Game`、`GameMatch`、`Run`

### 本專案目前主要資料表

* `trackers`
* `games`
* `game_matches`
* `runs`

### 常見寫法

```python
tracker = db.query(Tracker).filter(Tracker.id == tracker_id).first()
```

---

## 4. Alembic

### 用途

Alembic 是 SQLAlchemy 的 migration 工具，用來管理資料表結構變更。

### 在本專案中的使用

* 新增欄位
* 修改欄位名稱
* 同步 model 與資料庫 schema

### 本專案實際用到的情境

* 新增 `latest_update_date`
* `is_enabled` 改成 `is_active`
* `schedule` 改成 `update_frequency`

### 常用指令

```bash
alembic revision --autogenerate -m "add latest_update_date to games"
alembic upgrade head
```

### 注意事項

如果 model 已經改了，但資料庫還沒 upgrade，執行 API 時很容易出現這類錯誤：

```bash
no such column
table ... has no column named ...
```

---

## 5. Pydantic

### 用途

Pydantic 用來定義 API 的輸入與輸出格式，並進行資料驗證。

### 在本專案中的使用

* 定義 `TrackerCreate`
* 定義 `TrackerUpdate`
* 定義 `TrackerOut`
* 定義 `GameOut`
* 定義 `RunResult`
* 定義 `RunOut`

### 本專案目前驗證重點

* `query_json` 是否為合法 JSON 字串
* `query_json` 是否符合目前格式
* `update_frequency` 是否為合法值
* request / response 欄位格式是否正確

### 常見寫法

```python
from pydantic import BaseModel

class TrackerCreate(BaseModel):
    name: str
    source: str
```

---

## 6. APScheduler

### 用途

APScheduler 用來做定時任務，讓系統可以自動執行 tracker。

### 在本專案中的使用

* 每天自動跑 `daily`
* 每週自動跑 `weekly`

### 本專案的排程邏輯

* `run_daily_trackers()`
* `run_weekly_trackers()`

### 常見寫法

```python
scheduler.add_job(run_daily_trackers, "cron", hour=9, minute=0)
```

---

## 7. HTTPX

### 用途

HTTPX 用來發送 HTTP request，從外部 API 抓資料。

### 在本專案中的使用

* 串接 RAWG API
* 取得真實遊戲資料
* 依遊戲名稱搜尋資料

### 本專案實際用途

* `fetch_rawg_games()`
* 透過 `search` 參數查詢遊戲
* 把外部資料轉成目前 `Game` 可使用的格式

### 常見寫法

```python
response = httpx.get(url, params=params, timeout=20.0)
response.raise_for_status()
data = response.json()
```

---

## 8. python-dotenv

### 用途

python-dotenv 用來讀取 `.env` 檔案中的環境變數。

### 在本專案中的使用

* 讀取 `RAWG_API_KEY`
* 避免把 API key 直接寫死在程式碼裡

### 常見寫法

```python
from dotenv import load_dotenv
import os

load_dotenv()
RAWG_API_KEY = os.getenv("RAWG_API_KEY")
```

---

## 9. SQLite

### 用途

SQLite 是本專案目前開發階段使用的本地資料庫。

### 在本專案中的使用

* 儲存 tracker
* 儲存 game
* 儲存 run 紀錄
* 快速驗證 side project 功能

### 補充說明

SQLite 不是 `pip install` 的 Python 套件，而是 Python 可直接搭配使用的本地資料庫。
本專案是透過 SQLAlchemy 操作 SQLite。

### 目前資料庫檔案

```bash
game_radar.db
```

---

# 專案目前資料結構概念

## Tracker

負責定義要追蹤什麼條件。

目前主要欄位：

* `name`
* `source`
* `query_json`
* `update_frequency`
* `is_active`

---

## Game

負責儲存遊戲資料。

目前主要欄位：

* `external_id`
* `title`
* `studio`
* `region`
* `genre`
* `platform`
* `release_date`
* `latest_update_date`
* `source`

---

## Run

負責記錄每一次 tracker 執行的結果。

目前主要欄位：

* `tracker_id`
* `started_at`
* `ended_at`
* `status`
* `inserted_games`
* `matched_games`
* `error_message`

---

# query_json 格式

目前 `query_json` 使用新的 JSON 格式，不再使用舊的 `focus`。

## 格式範例

```json
{
  "regions": ["japan"],
  "games": ["elden ring"],
  "is_indie": false,
  "studios": ["FromSoftware"]
}
```

## 各欄位說明

### `regions`

代表遊戲的地區出處。
只做字串比對，不另外驗證是否為合法國家。

### `games`

代表遊戲名稱。
目前使用寬鬆比對。

### `is_indie`

代表是否為獨立開發遊戲。

### `studios`

代表開發商名稱。
目前使用寬鬆比對。

---

# Environment Setup（環境建置）

為了確保專案的獨立性與可重現性，建議使用 Python 虛擬環境（`venv`）。

## 1. 建立與啟動虛擬環境

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

成功啟動後，終端機前方會看到：

```bash
(.venv)
```

---

## 2. 安裝必要套件

先更新 pip：

```bash
python -m pip install --upgrade pip
```

再安裝目前專案需要的套件：

```bash
pip install fastapi uvicorn sqlalchemy alembic pydantic apscheduler httpx python-dotenv
```

如果你想把目前環境寫進 `requirements.txt`：

```bash
pip freeze > requirements.txt
```

如果你已經有 `requirements.txt`，也可以直接：

```bash
pip install -r requirements.txt
```

---

## 3. 建立 `.env`

請在專案根目錄建立 `.env` 檔案：

```env
RAWG_API_KEY=your_rawg_api_key
```

---

# Docker 使用方式

本專案支援使用 Docker 與 Docker Compose 啟動，方便在固定環境下執行 API。

## 1. 建立並啟動容器

在專案根目錄執行：

```bash
docker compose up -d --build
```

## 2. 執行資料庫 migration

第一次啟動後，請先執行：

```bash
docker compose exec api alembic upgrade head
```

這一步會建立 SQLite 資料表結構。

## 3. 測試 API

啟動成功後，可打開：

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

## 4. 資料庫位置

Docker Compose 會將容器內的 SQLite 資料庫掛載到本機：

```text
data/game_radar.db
```

這樣即使容器重建，資料仍可保留。

## 5. 停止容器

```bash
docker compose down
```

---

# 啟動伺服器測試

在專案 root 資料夾執行：

```bash
python -m uvicorn app.main:app --reload
```

---

# 基本測試

## 1. 健康檢查

打開瀏覽器輸入：

```bash
http://127.0.0.1:8000/health
```

如果成功，應該看到：

```json
{"status":"ok"}
```

這代表 FastAPI 有正常跑起來。

## 2. API 文件頁

FastAPI 啟動後，可以打開：

```bash
http://127.0.0.1:8000/docs
```

直接測試所有 API。

## 3. 更新資料庫欄位

如果 model 已改，但資料庫還沒同步，執行 API 很容易報錯。
這時要記得跑 migration：

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

---

# API 總表

## 1. System APIs

* `GET /health`
* `GET /v1/scheduler/status`

## 2. Tracker APIs

* `POST /v1/trackers`
* `GET /v1/trackers`
* `GET /v1/trackers/{tracker_id}`
* `PATCH /v1/trackers/{tracker_id}`
* `DELETE /v1/trackers/{tracker_id}`
* `GET /v1/trackers/active/{update_frequency}`

## 3. Run APIs

* `POST /v1/trackers/{tracker_id}/run`
* `POST /v1/trackers/run/{update_frequency}`
* `GET /v1/runs`
* `GET /v1/trackers/{tracker_id}/runs`

## 4. Game APIs

* `GET /v1/games`
* `GET /v1/trackers/{tracker_id}/games`
* `GET /v1/trackers/{tracker_id}/summary`

## 5. Dashboard APIs

* `GET /v1/dashboard/summary`
* `GET /v1/dashboard/recent-runs`
* `GET /v1/dashboard/recent-games`
* `GET /v1/dashboard/active-trackers`

---

# 最小操作流程

## 單筆 tracker 基本流程

1. 建立 tracker：`POST /v1/trackers`
2. 執行單筆 tracker：`POST /v1/trackers/{tracker_id}/run`
3. 查看該 tracker 的執行紀錄：`GET /v1/trackers/{tracker_id}/runs`
4. 查看該 tracker 配對到的遊戲：`GET /v1/trackers/{tracker_id}/games`
5. 查看單筆 tracker 摘要：`GET /v1/trackers/{tracker_id}/summary`

## 批次執行流程

1. 建立多筆 tracker，並設定 `update_frequency`
2. 執行指定頻率的 tracker：`POST /v1/trackers/run/{update_frequency}`
3. 查詢 active tracker：`GET /v1/trackers/active/{update_frequency}`
4. 查詢全部 run：`GET /v1/runs`
5. 查詢 dashboard：`GET /v1/dashboard/summary`

> 注意：
> 要先執行 tracker run，某筆 tracker 才會在 `/v1/trackers/{tracker_id}/runs` 與 `/v1/trackers/{tracker_id}/games` 查到資料。
> `GET /v1/runs` 是全部 tracker 的執行紀錄總表。

---

# 排程規則說明

* `is_active = true`：此 tracker 會被納入批次執行
* `is_active = false`：此 tracker 不會被批次執行
* `update_frequency = daily`：每天自動執行
* `update_frequency = weekly`：每週自動執行
* `update_frequency = manual`：只手動執行，不進入自動排程

目前排程器提供：

* 每天固定時間執行 daily trackers
* 每週固定時間執行 weekly trackers

可透過以下 API 檢查排程器狀態：

* `GET /v1/scheduler/status`

---

# 常用 API 範例

## 建立 tracker

```http
POST /v1/trackers
```

### 範例 request body

```json
{
  "name": "Japan Games Test",
  "source": "mock",
  "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
  "update_frequency": "daily",
  "is_active": true
}
```

## 執行單筆 tracker

```http
POST /v1/trackers/{tracker_id}/run
```

## 批次執行指定頻率的 tracker

```http
POST /v1/trackers/run/{update_frequency}
```

例如：

```http
POST /v1/trackers/run/daily
POST /v1/trackers/run/weekly
```

## 查詢全部 trackers

```http
GET /v1/trackers
```

## 查詢單一 tracker

```http
GET /v1/trackers/{tracker_id}
```

## 查詢全部 games

```http
GET /v1/games
```

## 查詢全部 runs

```http
GET /v1/runs
```

## 查詢某一筆 tracker 的執行紀錄

```http
GET /v1/trackers/{tracker_id}/runs
```

## 查詢某一筆 tracker 配對到的遊戲

```http
GET /v1/trackers/{tracker_id}/games
```

---

# 測試流程

本專案目前使用 Python 內建 `unittest` 進行 API 測試，測試會使用獨立的測試資料庫，不會污染正式開發資料庫。

## 本機執行測試

執行全部測試：

```bash
python -m unittest discover -s tests
```

如果測試成功，終端機會顯示類似：

```bash
Ran 22 tests in 0.xxxs

OK
```

## 目前測試涵蓋內容

* Tracker CRUD
* 單筆 tracker 執行
* 依頻率批次執行
* Dashboard APIs
* Scheduler 狀態
* 驗證錯誤與 404
* `is_active` / `manual` 規則測試

## 測試資料庫說明

測試會使用獨立的 SQLite 測試資料庫，例如：

```bash
test_game_radar.db
```

測試結束後會自動清除，不會影響正式開發資料庫。

---

# GitHub Actions

本專案已設定 GitHub Actions，自動在 `push` 或 `pull request` 時執行 API 測試。

Workflow 位置：

```bash
.github/workflows/python_install_test.yaml
```

目前 GitHub Actions 會自動執行：

1. 下載專案程式碼
2. 安裝 Python 3.11
3. 更新 pip
4. 安裝專案需要的套件
5. 執行 `python -m unittest discover -s tests`

如果流程成功，代表目前專案的核心 API 與測試都可正常運作。

---

# 開發紀錄提醒

每次修改以下內容後，都建議檢查是否需要 migration：

* `models.py`
* 欄位新增 / 刪除 / 改名
* 資料表 schema 變動

每完成一個階段，也建議做一次 Git 更新，例如：

```bash
git status
git add .
git commit -m "your update message"
git push
```

---

# 未來擴充方向

* 補更多真實遊戲資料來源
* 補 `latest_update_date` 真實來源
* 補 `publisher`、`description`、`official_url`
* 增加更多 tracker 條件
* 提供前端網站專案使用
* 增加使用者評論與評分功能（網站專案）
