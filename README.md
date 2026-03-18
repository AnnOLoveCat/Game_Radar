# Scholar_Radar
論文追蹤系統

## 1. Environment Setup (環境建置)

為了確保專案的獨立性與重現性，強烈建議使用 Python 虛擬環境 (`venv`) 進行開發。

### 1.1 建立與啟動虛擬環境

**Windows:**
```bash
# 建立名為 .venv 的虛擬環境
python -m venv .venv

# 啟動虛擬環境
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv .venv

# 啟動虛擬環境
source .venv/bin/activate
```
成功啟動後，您的終端機前方會出現 (.venv) 

### 1.2 安裝必要套件
在虛擬環境啟動的狀態下，安裝 YOLO 核心庫、標記工具與影像處理套件：
```bash
# 更新 pip
python -m pip install --upgrade pip

# 安裝 
pip install 
```


## 2. Open Server Test (啟動伺服器測試)
在root資料夾寫
```bash
python -m uvicorn app.main:app --reload
```

### 測試 1.1：先看健康檢查

打開瀏覽器輸入：
```bash
http://127.0.0.1:8000/health
```

如果成功，應該看到：

```bash
{"status":"ok"}
```
這代表 FastAPI 有正常跑起來。