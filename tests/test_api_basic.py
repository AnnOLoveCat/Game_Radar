# 1. 使用 FastAPI TestClient 直接測 API endpoint。
# 2. 使用獨立 SQLite 測試資料庫，避免影響正式資料庫。
# 3. 把相同類型的 200 / 400 / 404 / 422 回應合併成 table-driven tests，
#    避免每個 endpoint 都寫一個重複的 test function。
# 4. 驗證 tracker CRUD、tracker run、dashboard、frequency rules、schema validation、
#    query_json validation、missing tracker 等基本流程。
import os, unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import get_db
from app.models import Base


# 測試專用 SQLite DB 檔案，測試結束後會刪除。
TEST_DB_FILE = "test_game_radar.db"
TEST_DB_URL = "sqlite:///./{0}".format(TEST_DB_FILE)

# 建立測試用 SQLAlchemy engine。
# check_same_thread=False 是 SQLite 搭配 FastAPI TestClient 常見設定。
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False}
)

# 測試用 Session factory，後面會用它取代正式 get_db。
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# 覆蓋 FastAPI 原本的 get_db dependency。
# 測試時所有 API 都會使用 TestingSessionLocal，而不是正式資料庫 Session。
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestApiBasic(unittest.TestCase):
    @classmethod
    # 所有 test 開始前只執行一次。
    # 這裡會重建測試資料表、掛上測試 DB dependency、啟動 TestClient。
    def setUpClass(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        app.dependency_overrides[get_db] = override_get_db

        cls.client_manager = TestClient(app)
        cls.client = cls.client_manager.__enter__()

    @classmethod
    # 所有 test 結束後只執行一次。
    # 這裡會關閉 TestClient、清除 dependency override、刪除測試 DB。
    def tearDownClass(cls):
        cls.client_manager.__exit__(None, None, None)

        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

        if os.path.exists(TEST_DB_FILE):
            os.remove(TEST_DB_FILE)

    # =========================
    # Helper Methods
    # =========================

    # 共用 HTTP request helper。
    # table-driven test 可以用 method/path/json_body 決定要打哪個 API，避免重複寫 self.client.get/post/patch/delete。
    def _request(self, method, path, json_body=None):
        if method == "get":
            return self.client.get(path)

        if method == "post":
            return self.client.post(path, json=json_body)

        if method == "patch":
            return self.client.patch(path, json=json_body)

        if method == "delete":
            return self.client.delete(path)

        raise ValueError("Unsupported HTTP method: {0}".format(method))

    # 共用錯誤回應檢查 helper。
    # expected_detail：用來檢查 400 / 404 這種 detail 是字串的錯誤。
    # expected_field：用來檢查 FastAPI / Pydantic 422，確認錯誤位置 loc 有出現指定欄位。
    def _assert_error_response(
        self,
        response,
        expected_status_code,
        expected_detail=None,
        expected_field=None
    ):
        assert response.status_code == expected_status_code, response.json()

        data = response.json()

        assert "detail" in data

        # 400 / 404 類型錯誤通常是 detail 字串，例如 "Tracker not found"。
        if expected_detail is not None:
            assert data.get("detail") == expected_detail

        # 422 類型錯誤通常是 detail list，要從 loc 裡確認是哪個欄位錯。
        if expected_field is not None:
            error_locs = [
                error.get("loc", [])
                for error in data.get("detail", [])
            ]

            assert any(expected_field in loc for loc in error_locs)

    # 共用 list 回應檢查 helper。
    # 適合檢查 GET list endpoints，例如 /v1/trackers、/runs、/games、dashboard list。
    def _assert_list_response(
        self,
        response,
        expected_status_code=200,
        min_length=None,
        required_keys=None
    ):
        assert response.status_code == expected_status_code, response.json()

        data = response.json()

        assert isinstance(data, list)

        if min_length is not None:
            assert len(data) >= min_length

        # 如果指定 required_keys，就檢查第一筆資料是否具有必要欄位。
        if required_keys:
            assert len(data) >= 1

            first_item = data[0]
            for key in required_keys:
                assert key in first_item

        return data

    # 建立一份合法的 query_json 測試資料。
    # overrides 可以故意覆蓋某個欄位，例如 regions="japan"，用來測錯誤型別。
    def _build_query_json(self, **overrides):
        query_json = {
            "target_game": {
                "title": "Elden Ring",
                "platform_hints": ["PC", "PlayStation", "Xbox"]
            },
            "sources_to_check": ["mock"],
            "regions": ["japan"],
            "genres": ["Action RPG"],
            "platforms": ["PC", "Xbox"],
            "user_review": {
                "has_played": True,
                "platform_played": "PC",
                "playtime_hours": 40,
                "is_recommended": True,
                "review_title": "高難度但很有探索感",
                "review_text": "這款遊戲的地圖探索、戰鬥節奏和 Boss 設計都很有特色，但新手一開始會比較容易挫折。",
                "pros": ["探索感強", "戰鬥有挑戰性", "世界觀完整"],
                "cons": ["新手門檻高", "部分 Boss 難度偏高"],
                "suitable_for": ["喜歡高難度動作 RPG 的玩家"],
                "not_suitable_for": ["不喜歡反覆挑戰 Boss 的玩家"]
            }
        }

        query_json.update(overrides)

        return query_json

    # 建立 POST /v1/trackers 或相關測試會用到的 request body。
    # 預設會放入合法 query_json，避免每個測試重複寫完整 payload。
    def _build_tracker_payload(
        self,
        name,
        update_frequency="daily",
        is_active=True,
        source="mock",
        query_json=None
    ):
        if query_json is None:
            query_json = self._build_query_json()

        return {
            "name": name,
            "source": source,
            "query_json": query_json,
            "update_frequency": update_frequency,
            "is_active": is_active,
        }

    # 建立 tracker 的共用 helper。
    # 很多測試都要先有 tracker_id，例如 PATCH、DELETE、RUN、SUMMARY、GAMES、RUNS。
    def _create_tracker(
        self,
        name,
        update_frequency="daily",
        is_active=True,
        source="mock",
        query_json=None
    ):
        payload = self._build_tracker_payload(
            name=name,
            update_frequency=update_frequency,
            is_active=is_active,
            source=source,
            query_json=query_json
        )

        response = self.client.post("/v1/trackers", json=payload)
        assert response.status_code == 200, response.json()

        data = response.json()
        tracker_id = data.get("id")

        assert tracker_id is not None

        return tracker_id, data

    # 執行單筆 tracker 的共用 helper。
    # 成功後會產生 Run 紀錄與 GameMatch / Game 資料，後續 dashboard、runs、games 測試會用到。
    def _run_tracker_once(self, tracker_id):
        response = self.client.post("/v1/trackers/{0}/run".format(tracker_id))

        assert response.status_code == 200, response.json()

        return response.json()

    # 檢查 POST /v1/trackers 時 query_json 內部結構錯誤。
    # 這裡測的是 service-level validation，所以通常預期 400，不是 Pydantic 422。
    def _assert_create_tracker_query_json_error(
        self,
        name,
        query_json,
        expected_detail,
        expected_status_code=400
    ):
        payload = self._build_tracker_payload(
            name=name,
            query_json=query_json
        )

        response = self.client.post("/v1/trackers", json=payload)

        self._assert_error_response(
            response=response,
            expected_status_code=expected_status_code,
            expected_detail=expected_detail
        )

    # 檢查 PATCH /v1/trackers/{tracker_id} 時 query_json 內部結構錯誤。
    # 先建立一筆 tracker，再用錯誤 query_json 去 PATCH。
    def _assert_update_tracker_query_json_error(
        self,
        query_json,
        expected_detail,
        expected_status_code=400
    ):
        tracker_id, _ = self._create_tracker(
            name="Pytest Update Query JSON Validation Tracker"
        )

        update_payload = {
            "query_json": query_json
        }

        response = self.client.patch(
            "/v1/trackers/{0}".format(tracker_id),
            json=update_payload
        )

        self._assert_error_response(
            response=response,
            expected_status_code=expected_status_code,
            expected_detail=expected_detail
        )

    # =========================
    # System API Tests
    # =========================

    # 測 system endpoint 的基本回應格式。
    # /health 要回固定狀態；/v1/scheduler/status 要回 scheduler 狀態欄位。
    def test_system_endpoints_return_expected_shape(self):
        test_cases = [
            {
                "name": "Health check",
                "method": "get",
                "path": "/health",
                "expected_status_code": 200,
                "expected_body": {"status": "ok"},
            },
            {
                "name": "Scheduler status",
                "method": "get",
                "path": "/v1/scheduler/status",
                "expected_status_code": 200,
                "required_keys": ["scheduler_running", "job_count", "jobs"],
            },
        ]

        # 使用 subTest 讓同一個 test function 可以跑多個 endpoint，
        # 其中一個 case 失敗時也能知道是哪個 case 出錯。
        for case in test_cases:
            with self.subTest(case=case["name"]):
                response = self._request(case["method"], case["path"])

                assert response.status_code == case["expected_status_code"], response.json()

                data = response.json()

                if "expected_body" in case:
                    assert data == case["expected_body"]

                if "required_keys" in case:
                    for key in case["required_keys"]:
                        assert key in data

                    assert data.get("scheduler_running") is True
                    assert isinstance(data.get("jobs"), list)
                    assert data.get("job_count") >= 2

    # =========================
    # Tracker CRUD Tests
    # =========================

    # 測 Tracker CRUD 成功流程。
    # 把 create/list/get/update/delete 串成一個完整情境，避免每個 200 成功結果分散成太多重複 test。
    def test_tracker_crud_success_flow(self):
        tracker_id, created_data = self._create_tracker("Pytest CRUD Tracker")

        assert created_data.get("name") == "Pytest CRUD Tracker"
        assert created_data.get("source") == "mock"
        assert created_data.get("update_frequency") == "daily"
        assert created_data.get("is_active") is True

        created_query_json = created_data.get("query_json")
        assert isinstance(created_query_json, dict)
        assert created_query_json["target_game"]["title"] == "Elden Ring"
        assert "user_review" in created_query_json

        list_response = self.client.get("/v1/trackers")
        self._assert_list_response(list_response)

        get_response = self.client.get("/v1/trackers/{0}".format(tracker_id))
        assert get_response.status_code == 200, get_response.json()

        get_data = get_response.json()
        assert get_data.get("id") == tracker_id
        assert isinstance(get_data.get("query_json"), dict)
        assert get_data["query_json"]["target_game"]["title"] == "Elden Ring"

        update_payload = {
            "name": "Pytest Updated CRUD Tracker",
            "update_frequency": "weekly",
            "is_active": False,
        }

        update_response = self.client.patch(
            "/v1/trackers/{0}".format(tracker_id),
            json=update_payload
        )

        assert update_response.status_code == 200, update_response.json()

        updated_data = update_response.json()

        assert updated_data.get("id") == tracker_id
        assert updated_data.get("name") == "Pytest Updated CRUD Tracker"
        assert updated_data.get("update_frequency") == "weekly"
        assert updated_data.get("is_active") is False

        delete_response = self.client.delete("/v1/trackers/{0}".format(tracker_id))
        assert delete_response.status_code == 200, delete_response.json()

        deleted_get_response = self.client.get("/v1/trackers/{0}".format(tracker_id))
        self._assert_error_response(
            response=deleted_get_response,
            expected_status_code=404,
            expected_detail="Tracker not found"
        )

    # 測 PATCH 更新 query_json object。
    # 重點是確認 query_json 可以用 object 更新，而且回傳時仍然是 dict/object，不是 JSON 字串。
    def test_update_tracker_query_json_object(self):
        tracker_id, _ = self._create_tracker("Pytest Update Query JSON Tracker")

        update_payload = {
            "query_json": {
                "target_game": {
                    "title": "Hades II",
                    "platform_hints": ["PC", "Steam"]
                },
                "sources_to_check": ["mock"],
                "regions": ["usa"],
                "genres": ["Action Roguelike"],
                "platforms": ["PC"],
                "user_review": {
                    "has_played": True,
                    "platform_played": "PC",
                    "playtime_hours": 8,
                    "is_recommended": True,
                    "review_title": "節奏快，戰鬥爽感強",
                    "review_text": "Hades II 的戰鬥節奏很快，角色成長和反覆挑戰的設計很適合喜歡 Roguelike 的玩家。",
                    "pros": ["戰鬥節奏快", "角色成長明確"],
                    "cons": ["需要反覆挑戰"],
                    "suitable_for": ["喜歡 Roguelike 的玩家"],
                    "not_suitable_for": ["不喜歡重複刷關的玩家"]
                }
            }
        }

        update_response = self.client.patch(
            "/v1/trackers/{0}".format(tracker_id),
            json=update_payload
        )

        assert update_response.status_code == 200, update_response.json()

        updated_data = update_response.json()

        assert updated_data.get("id") == tracker_id

        query_json = updated_data.get("query_json")

        assert isinstance(query_json, dict)
        assert query_json["target_game"]["title"] == "Hades II"
        assert "user_review" in query_json

    # =========================
    # Tracker Run Flow Tests
    # =========================

    # 測 tracker run 成功後的資料流。
    # 執行 tracker 後，再一起檢查 runs、games、dashboard recent-runs、dashboard recent-games 的 list 回應。
    def test_tracker_run_success_flow(self):
        tracker_id, _ = self._create_tracker("Pytest Run Flow Tracker")

        run_data = self._run_tracker_once(tracker_id)

        assert run_data.get("tracker_id") == tracker_id
        assert "inserted_games" in run_data
        assert "matched_games" in run_data

        # 這些 endpoint 都是 tracker run 成功後才會有資料，
        # 所以放在同一個成功流程裡檢查。
        endpoint_cases = [
            {
                "name": "Tracker runs endpoint",
                "path": "/v1/trackers/{0}/runs".format(tracker_id),
                "required_keys": ["id", "tracker_id", "status", "started_at"],
            },
            {
                "name": "Tracker games endpoint",
                "path": "/v1/trackers/{0}/games".format(tracker_id),
                "required_keys": ["id", "external_id", "title", "source"],
            },
            {
                "name": "Dashboard recent runs",
                "path": "/v1/dashboard/recent-runs",
                "required_keys": ["id", "tracker_id", "status"],
            },
            {
                "name": "Dashboard recent games",
                "path": "/v1/dashboard/recent-games",
                "required_keys": ["id", "external_id", "title", "source"],
            },
        ]

        for case in endpoint_cases:
            with self.subTest(case=case["name"]):
                response = self.client.get(case["path"])
                self._assert_list_response(
                    response=response,
                    min_length=1,
                    required_keys=case["required_keys"]
                )

    # 測 tracker summary 回應。
    # summary 結構比較特殊，會包含 tracker 基本資料、matched_games_count、latest_run，所以保留獨立測試。
    def test_tracker_summary(self):
        tracker_id, _ = self._create_tracker("Pytest Summary Tracker")

        self._run_tracker_once(tracker_id)

        summary_response = self.client.get("/v1/trackers/{0}/summary".format(tracker_id))

        assert summary_response.status_code == 200, summary_response.json()

        summary_data = summary_response.json()

        assert summary_data.get("tracker_id") == tracker_id
        assert summary_data.get("name") == "Pytest Summary Tracker"
        assert "matched_games_count" in summary_data
        assert "latest_run" in summary_data

        query_json = summary_data.get("query_json")

        assert isinstance(query_json, dict)
        assert "target_game" in query_json
        assert query_json["target_game"]["title"] == "Elden Ring"

    # =========================
    # Dashboard API Tests
    # =========================

    # 測 Dashboard API 的基本回應格式。
    # summary 是 object；active-trackers 是 list，兩者用同一個 table-driven test 管理。
    def test_dashboard_endpoints_return_expected_shape(self):
        self._create_tracker("Pytest Active Tracker")

        endpoint_cases = [
            {
                "name": "Dashboard summary",
                "method": "get",
                "path": "/v1/dashboard/summary",
                "response_type": "object",
                "required_keys": [
                    "tracker_count",
                    "active_tracker_count",
                    "game_count",
                    "run_count",
                ],
            },
            {
                "name": "Dashboard active trackers",
                "method": "get",
                "path": "/v1/dashboard/active-trackers",
                "response_type": "list",
                "required_keys": ["id", "name", "update_frequency", "is_active"],
            },
        ]

        for case in endpoint_cases:
            with self.subTest(case=case["name"]):
                response = self._request(case["method"], case["path"])

                assert response.status_code == 200, response.json()

                data = response.json()

                if case["response_type"] == "object":
                    assert isinstance(data, dict)
                    for key in case["required_keys"]:
                        assert key in data

                if case["response_type"] == "list":
                    assert isinstance(data, list)
                    assert len(data) >= 1
                    for key in case["required_keys"]:
                        assert key in data[0]

    # =========================
    # Frequency Rule Tests
    # =========================

    # 測 update_frequency 成功規則。
    # active/daily 應該查得到 daily tracker；run/daily 應該批次執行 daily trackers。
    def test_frequency_rule_success_cases(self):
        self._create_tracker("Pytest Daily Tracker", update_frequency="daily")
        self._create_tracker("Pytest Weekly Tracker", update_frequency="weekly")

        daily_active_response = self.client.get("/v1/trackers/active/daily")
        daily_active_data = self._assert_list_response(
            response=daily_active_response,
            min_length=1,
            required_keys=["id", "name", "update_frequency"]
        )

        assert any(
            item.get("update_frequency") == "daily"
            for item in daily_active_data
        )

        self._create_tracker("Pytest Batch Daily Tracker 1", update_frequency="daily")
        self._create_tracker("Pytest Batch Daily Tracker 2", update_frequency="daily")
        self._create_tracker("Pytest Batch Weekly Tracker", update_frequency="weekly")

        batch_response = self.client.post("/v1/trackers/run/daily")
        batch_data = self._assert_list_response(
            response=batch_response,
            min_length=2,
            required_keys=["tracker_id", "name", "status", "inserted_games", "matched_games"]
        )

        assert all("error" in item for item in batch_data)

    # 測 inactive 與 manual tracker 的 frequency 規則。
    # inactive tracker 不應出現在 active list / batch run；manual tracker 不應進 daily/weekly batch，但可以單筆 run。
    def test_inactive_and_manual_tracker_frequency_rules(self):
        self._create_tracker(
            "Pytest Active Daily Tracker",
            update_frequency="daily",
            is_active=True
        )
        inactive_tracker_id, _ = self._create_tracker(
            "Pytest Inactive Daily Tracker",
            update_frequency="daily",
            is_active=False
        )
        manual_tracker_id, _ = self._create_tracker(
            "Pytest Manual Tracker",
            update_frequency="manual",
            is_active=True
        )

        active_list_response = self.client.get("/v1/trackers/active/daily")
        active_list_data = self._assert_list_response(active_list_response)

        active_tracker_ids = [item.get("id") for item in active_list_data]
        assert inactive_tracker_id not in active_tracker_ids

        batch_cases = [
            {
                "name": "Daily batch excludes inactive and manual trackers",
                "path": "/v1/trackers/run/daily",
                "excluded_tracker_ids": [inactive_tracker_id, manual_tracker_id],
            },
            {
                "name": "Weekly batch excludes manual tracker",
                "path": "/v1/trackers/run/weekly",
                "excluded_tracker_ids": [manual_tracker_id],
            },
        ]

        for case in batch_cases:
            with self.subTest(case=case["name"]):
                response = self.client.post(case["path"])
                batch_data = self._assert_list_response(response)

                batch_tracker_ids = [item.get("tracker_id") for item in batch_data]

                for tracker_id in case["excluded_tracker_ids"]:
                    assert tracker_id not in batch_tracker_ids

        manual_run_data = self._run_tracker_once(manual_tracker_id)

        assert manual_run_data.get("tracker_id") == manual_tracker_id
        assert "inserted_games" in manual_run_data
        assert "matched_games" in manual_run_data

    # =========================
    # Validation / Error Tests
    # =========================

    # 測 schema-level 錯誤，預期由 FastAPI / Pydantic 回 422。
    # 包含 request body 欄位型別錯、Enum 值錯，以及 path parameter Enum 值錯。
    # 這裡不是 service-level 400。
    def test_schema_errors_return_422(self):
        tracker_id, _ = self._create_tracker(
            name="Pytest Schema Validation Tracker"
        )

        test_cases = [
            {
                "name": "POST /v1/trackers with query_json as string",
                "method": "post",
                "path": "/v1/trackers",
                "json_body": self._build_tracker_payload(
                    name="Pytest Invalid Query JSON",
                    query_json="{invalid_json}"
                ),
                "expected_field": "query_json",
            },
            {
                "name": "POST /v1/trackers with source = steam",
                "method": "post",
                "path": "/v1/trackers",
                "json_body": self._build_tracker_payload(
                    name="Pytest Invalid Source",
                    source="steam"
                ),
                "expected_field": "source",
            },
            {
                "name": "PATCH /v1/trackers/{tracker_id} with source = steam",
                "method": "patch",
                "path": "/v1/trackers/{0}".format(tracker_id),
                "json_body": {
                    "source": "steam"
                },
                "expected_field": "source",
            },
            {
                "name": "POST /v1/trackers with update_frequency = hourly",
                "method": "post",
                "path": "/v1/trackers",
                "json_body": self._build_tracker_payload(
                    name="Pytest Invalid Frequency",
                    update_frequency="hourly"
                ),
                "expected_field": "update_frequency",
            },
            {
                "name": "PATCH /v1/trackers/{tracker_id} with update_frequency = hourly",
                "method": "patch",
                "path": "/v1/trackers/{0}".format(tracker_id),
                "json_body": {
                    "update_frequency": "hourly"
                },
                "expected_field": "update_frequency",
            },
            {
                "name": "GET /v1/trackers/active/hourly",
                "method": "get",
                "path": "/v1/trackers/active/hourly",
                "expected_field": "update_frequency",
            },
            {
                "name": "POST /v1/trackers/run/hourly",
                "method": "post",
                "path": "/v1/trackers/run/hourly",
                "expected_field": "update_frequency",
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                response = self._request(
                    method=case["method"],
                    path=case["path"],
                    json_body=case.get("json_body")
                )

                self._assert_error_response(
                    response=response,
                    expected_status_code=422,
                    expected_field=case["expected_field"]
                )


    # 測 query_json 多出不支援欄位 unknown_key。
    # POST 建立與 PATCH 更新都應該走同一個 service-level validation，回 400。
    def test_unsupported_query_json_key_returns_422(self):
        tracker_id, _ = self._create_tracker(
            name="Pytest Unsupported Query JSON Key Update Target"
        )

        test_cases = [
            {
                "name": "POST /v1/trackers query_json.unknown_key",
                "method": "post",
                "path": "/v1/trackers",
                "json_body": self._build_tracker_payload(
                    name="Pytest Unsupported Query JSON Key",
                    query_json=self._build_query_json(
                        unknown_key="not allowed"
                    )
                ),
                "expected_field": "unknown_key",
            },
            {
                "name": "PATCH /v1/trackers/{tracker_id} query_json.unknown_key",
                "method": "patch",
                "path": "/v1/trackers/{0}".format(tracker_id),
                "json_body": {
                    "query_json": self._build_query_json(
                        unknown_key="not allowed"
                    )
                },
                "expected_field": "unknown_key",
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                response = self._request(
                    method=case["method"],
                    path=case["path"],
                    json_body=case["json_body"]
                )

                self._assert_error_response(
                    response=response,
                    expected_status_code=422,
                    expected_field=case["expected_field"]
                )


    # 測 query_json 內部欄位型別錯誤，預期回 400。
    # 使用雙層 table-driven test：同一批欄位錯誤同時測 POST create 與 PATCH update。
    def test_invalid_query_json_field_types_return_422(self):
        tracker_id, _ = self._create_tracker(
            name="Pytest Invalid Query JSON Type Update Target"
        )

        field_cases = [
            {
                "field_name": "target_game",
                "query_json": self._build_query_json(target_game="Elden Ring"),
                "expected_field": "target_game",
            },
            {
                "field_name": "sources_to_check",
                "query_json": self._build_query_json(sources_to_check="mock"),
                "expected_field": "sources_to_check",
            },
            {
                "field_name": "regions",
                "query_json": self._build_query_json(regions="japan"),
                "expected_field": "regions",
            },
            {
                "field_name": "genres",
                "query_json": self._build_query_json(genres="Action RPG"),
                "expected_field": "genres",
            },
            {
                "field_name": "platforms",
                "query_json": self._build_query_json(platforms="PC"),
                "expected_field": "platforms",
            },
            {
                "field_name": "user_review",
                "query_json": self._build_query_json(user_review="good game"),
                "expected_field": "user_review",
            },
            {
                "field_name": "games",
                "query_json": self._build_query_json(games="Elden Ring"),
                "expected_field": "games",
            },
            {
                "field_name": "studios",
                "query_json": self._build_query_json(studios="FromSoftware"),
                "expected_field": "studios",
            },
            {
                "field_name": "is_indie",
                "query_json": self._build_query_json(is_indie="false"),
                "expected_field": "is_indie",
            },
        ]

        operation_cases = [
            {
                "name": "POST /v1/trackers",
                "method": "post",
                "path": "/v1/trackers",
            },
            {
                "name": "PATCH /v1/trackers/{tracker_id}",
                "method": "patch",
                "path": "/v1/trackers/{0}".format(tracker_id),
            },
        ]

        for operation_case in operation_cases:
            for field_case in field_cases:
                with self.subTest(
                    operation=operation_case["name"],
                    field=field_case["field_name"]
                ):
                    if operation_case["method"] == "post":
                        json_body = self._build_tracker_payload(
                            name="Pytest Invalid {0} Type".format(field_case["field_name"]),
                            query_json=field_case["query_json"]
                        )
                    else:
                        json_body = {
                            "query_json": field_case["query_json"]
                        }

                    response = self._request(
                        method=operation_case["method"],
                        path=operation_case["path"],
                        json_body=json_body
                    )

                    self._assert_error_response(
                        response=response,
                        expected_status_code=422,
                        expected_field=field_case["expected_field"]
                    )

    # 測 tracker_id 不存在時的 404。
    # GET / PATCH / DELETE 都是同一種錯誤規則：path parameter tracker_id 找不到資料。
    def test_missing_tracker_paths_return_404(self):
        test_cases = [
            {
                "name": "GET /v1/trackers/{tracker_id}",
                "method": "get",
                "path": "/v1/trackers/999999",
            },
            {
                "name": "PATCH /v1/trackers/{tracker_id}",
                "method": "patch",
                "path": "/v1/trackers/999999",
                "json_body": {
                    "name": "Pytest Missing Updated Tracker",
                    "update_frequency": "weekly",
                    "is_active": False,
                },
            },
            {
                "name": "DELETE /v1/trackers/{tracker_id}",
                "method": "delete",
                "path": "/v1/trackers/999999",
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                response = self._request(
                    method=case["method"],
                    path=case["path"],
                    json_body=case.get("json_body")
                )

                self._assert_error_response(
                    response=response,
                    expected_status_code=404,
                    expected_detail="Tracker not found"
                )


if __name__ == "__main__":
    unittest.main()
