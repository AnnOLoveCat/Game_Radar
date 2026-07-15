import os, unittest, json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import get_db
from app.models import Base


TEST_DB_FILE = "test_game_radar.db"
TEST_DB_URL = "sqlite:///./{0}".format(TEST_DB_FILE)

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestApiBasic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        app.dependency_overrides[get_db] = override_get_db

        cls.client_manager = TestClient(app)
        cls.client = cls.client_manager.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_manager.__exit__(None, None, None)

        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

        if os.path.exists(TEST_DB_FILE):
            os.remove(TEST_DB_FILE)

    # =========================
    # Scheduler API Tests
    # =========================

    def test_scheduler_status(self):
        response = self.client.get("/v1/scheduler/status")
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("scheduler_running", data)
        self.assertIn("job_count", data)
        self.assertIn("jobs", data)

        self.assertTrue(data.get("scheduler_running"))
        self.assertTrue(isinstance(data.get("jobs"), list))
        self.assertTrue(data.get("job_count") >= 2)

    # =========================
    # Helper Methods
    # =========================

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

    def _run_tracker_once(self, tracker_id):
        response = self.client.post("/v1/trackers/{0}/run".format(tracker_id))

        assert response.status_code == 200, response.json()

        return response.json()
    
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

        assert response.status_code == expected_status_code, response.json()

        data = response.json()

        assert "detail" in data
        assert data.get("detail") == expected_detail

    # =========================
    # Basic API Tests
    # =========================

    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_create_tracker(self):
        tracker_id, data = self._create_tracker("Pytest Japan Tracker")

        assert tracker_id is not None
        assert data.get("name") == "Pytest Japan Tracker"
        assert data.get("source") == "mock"
        assert data.get("update_frequency") == "daily"
        assert data.get("is_active") is True

        query_json = data.get("query_json")

        assert isinstance(query_json, dict)
        assert "target_game" in query_json
        assert "user_review" in query_json
        assert query_json["target_game"]["title"] == "Elden Ring"

    def test_list_trackers(self):
        response = self.client.get("/v1/trackers")

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    # =========================
    # Tracker CRUD Tests
    # =========================

    def test_update_tracker(self):
        tracker_id, _ = self._create_tracker("Pytest Update Tracker")

        update_payload = {
            "name": "Pytest Updated Tracker",
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
        assert updated_data.get("name") == "Pytest Updated Tracker"
        assert updated_data.get("update_frequency") == "weekly"
        assert updated_data.get("is_active") is False

    def test_delete_tracker(self):
        tracker_id, _ = self._create_tracker("Pytest Delete Tracker")

        delete_response = self.client.delete("/v1/trackers/{0}".format(tracker_id))
        self.assertEqual(delete_response.status_code, 200)

        get_response = self.client.get("/v1/trackers/{0}".format(tracker_id))
        self.assertEqual(get_response.status_code, 404)

    def test_get_missing_tracker(self):
        response = self.client.get("/v1/trackers/999999")

        self.assertEqual(response.status_code, 404)

        data = response.json()
        self.assertIn("detail", data)
        self.assertEqual(data.get("detail"), "Tracker not found")

    def test_get_tracker_returns_query_json_object(self):
        tracker_id, _ = self._create_tracker("Pytest Get Tracker Query JSON")

        response = self.client.get("/v1/trackers/{0}".format(tracker_id))

        assert response.status_code == 200, response.json()

        data = response.json()
        query_json = data.get("query_json")

        assert isinstance(query_json, dict)
        assert "target_game" in query_json
        assert query_json["target_game"]["title"] == "Elden Ring"
        assert "user_review" in query_json

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

    def test_run_tracker(self):
        tracker_id, _ = self._create_tracker("Pytest Run Tracker")

        run_data = self._run_tracker_once(tracker_id)

        self.assertEqual(run_data.get("tracker_id"), tracker_id)
        self.assertIn("inserted_games", run_data)
        self.assertIn("matched_games", run_data)

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

    def test_tracker_runs_endpoint(self):
        tracker_id, _ = self._create_tracker("Pytest Tracker Runs Endpoint")

        self._run_tracker_once(tracker_id)

        runs_response = self.client.get("/v1/trackers/{0}/runs".format(tracker_id))
        self.assertEqual(runs_response.status_code, 200)

        runs_data = runs_response.json()

        self.assertIsInstance(runs_data, list)
        self.assertTrue(len(runs_data) >= 1)

        first_item = runs_data[0]
        self.assertIn("id", first_item)
        self.assertIn("tracker_id", first_item)
        self.assertIn("status", first_item)
        self.assertIn("started_at", first_item)

    def test_tracker_games_endpoint(self):
        tracker_id, _ = self._create_tracker("Pytest Tracker Games Endpoint")

        self._run_tracker_once(tracker_id)

        games_response = self.client.get("/v1/trackers/{0}/games".format(tracker_id))
        self.assertEqual(games_response.status_code, 200)

        games_data = games_response.json()

        self.assertIsInstance(games_data, list)
        self.assertTrue(len(games_data) >= 1)

        first_item = games_data[0]
        self.assertIn("id", first_item)
        self.assertIn("external_id", first_item)
        self.assertIn("title", first_item)
        self.assertIn("source", first_item)

    # =========================
    # Dashboard API Tests
    # =========================

    def test_dashboard_summary(self):
        response = self.client.get("/v1/dashboard/summary")

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("tracker_count", data)
        self.assertIn("active_tracker_count", data)
        self.assertIn("game_count", data)
        self.assertIn("run_count", data)

    def test_dashboard_recent_runs(self):
        tracker_id, _ = self._create_tracker("Pytest Recent Runs Tracker")

        self._run_tracker_once(tracker_id)

        recent_runs_response = self.client.get("/v1/dashboard/recent-runs")
        self.assertEqual(recent_runs_response.status_code, 200)

        recent_runs_data = recent_runs_response.json()

        self.assertIsInstance(recent_runs_data, list)
        self.assertTrue(len(recent_runs_data) >= 1)

        first_item = recent_runs_data[0]
        self.assertIn("id", first_item)
        self.assertIn("tracker_id", first_item)
        self.assertIn("status", first_item)

    def test_dashboard_recent_games(self):
        tracker_id, _ = self._create_tracker("Pytest Recent Games Tracker")

        self._run_tracker_once(tracker_id)

        recent_games_response = self.client.get("/v1/dashboard/recent-games")
        self.assertEqual(recent_games_response.status_code, 200)

        recent_games_data = recent_games_response.json()

        self.assertIsInstance(recent_games_data, list)
        self.assertTrue(len(recent_games_data) >= 1)

        first_item = recent_games_data[0]
        self.assertIn("id", first_item)
        self.assertIn("external_id", first_item)
        self.assertIn("title", first_item)
        self.assertIn("source", first_item)

    def test_dashboard_active_trackers(self):
        self._create_tracker("Pytest Active Tracker")

        active_response = self.client.get("/v1/dashboard/active-trackers")
        self.assertEqual(active_response.status_code, 200)

        active_data = active_response.json()

        self.assertIsInstance(active_data, list)
        self.assertTrue(len(active_data) >= 1)

        first_item = active_data[0]
        self.assertIn("id", first_item)
        self.assertIn("name", first_item)
        self.assertIn("update_frequency", first_item)
        self.assertIn("is_active", first_item)

    # =========================
    # Frequency Rule Tests
    # =========================

    def test_active_trackers_by_frequency(self):
        self._create_tracker("Pytest Daily Tracker", update_frequency="daily")
        self._create_tracker("Pytest Weekly Tracker", update_frequency="weekly")

        response_daily = self.client.get("/v1/trackers/active/daily")
        self.assertEqual(response_daily.status_code, 200)

        daily_data = response_daily.json()
        self.assertIsInstance(daily_data, list)
        self.assertTrue(len(daily_data) >= 1)

        first_item = daily_data[0]
        self.assertIn("id", first_item)
        self.assertIn("name", first_item)
        self.assertIn("update_frequency", first_item)
        self.assertEqual(first_item.get("update_frequency"), "daily")

    def test_run_trackers_by_frequency(self):
        self._create_tracker("Pytest Batch Daily Tracker 1", update_frequency="daily")
        self._create_tracker("Pytest Batch Daily Tracker 2", update_frequency="daily")
        self._create_tracker("Pytest Batch Weekly Tracker", update_frequency="weekly")

        batch_response = self.client.post("/v1/trackers/run/daily")
        self.assertEqual(batch_response.status_code, 200)

        batch_data = batch_response.json()

        self.assertIsInstance(batch_data, list)
        self.assertTrue(len(batch_data) >= 2)

        first_item = batch_data[0]
        self.assertIn("tracker_id", first_item)
        self.assertIn("name", first_item)
        self.assertIn("status", first_item)
        self.assertIn("inserted_games", first_item)
        self.assertIn("matched_games", first_item)

    def test_inactive_tracker_not_in_active_or_batch_run(self):
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

        active_list_response = self.client.get("/v1/trackers/active/daily")
        self.assertEqual(active_list_response.status_code, 200)

        active_list_data = active_list_response.json()
        self.assertIsInstance(active_list_data, list)

        inactive_ids = [item.get("id") for item in active_list_data]
        self.assertTrue(inactive_tracker_id not in inactive_ids)

        batch_response = self.client.post("/v1/trackers/run/daily")
        self.assertEqual(batch_response.status_code, 200)

        batch_data = batch_response.json()
        self.assertIsInstance(batch_data, list)

        batch_tracker_ids = [item.get("tracker_id") for item in batch_data]
        self.assertTrue(inactive_tracker_id not in batch_tracker_ids)

    def test_manual_tracker_not_in_daily_or_weekly_batch_run(self):
        tracker_id, _ = self._create_tracker(
            "Pytest Manual Tracker",
            update_frequency="manual",
            is_active=True
        )

        daily_response = self.client.post("/v1/trackers/run/daily")
        self.assertEqual(daily_response.status_code, 200)

        daily_data = daily_response.json()
        self.assertIsInstance(daily_data, list)

        daily_tracker_ids = [item.get("tracker_id") for item in daily_data]
        self.assertTrue(tracker_id not in daily_tracker_ids)

        weekly_response = self.client.post("/v1/trackers/run/weekly")
        self.assertEqual(weekly_response.status_code, 200)

        weekly_data = weekly_response.json()
        self.assertIsInstance(weekly_data, list)

        weekly_tracker_ids = [item.get("tracker_id") for item in weekly_data]
        self.assertTrue(tracker_id not in weekly_tracker_ids)

    def test_manual_tracker_can_run_single(self):
        tracker_id, _ = self._create_tracker(
            "Pytest Manual Single Run Tracker",
            update_frequency="manual",
            is_active=True
        )

        run_data = self._run_tracker_once(tracker_id)

        self.assertEqual(run_data.get("tracker_id"), tracker_id)
        self.assertIn("inserted_games", run_data)
        self.assertIn("matched_games", run_data)

    # =========================
    # Validation / Error Tests
    # =========================

    def test_create_tracker_invalid_query_json(self):
        payload = self._build_tracker_payload(
            name="Pytest Invalid Query JSON",
            query_json="{invalid_json}"
        )

        response = self.client.post("/v1/trackers", json=payload)

        assert response.status_code == 422, response.json()

        data = response.json()

        assert "detail" in data


    def test_create_tracker_invalid_update_frequency(self):
        payload = self._build_tracker_payload(
            name="Pytest Invalid Frequency",
            update_frequency="hourly"
        )

        response = self.client.post("/v1/trackers", json=payload)

        assert response.status_code == 422, response.json()

        data = response.json()

        assert "detail" in data

        error_locs = [
            error.get("loc", [])
            for error in data.get("detail", [])
        ]

        assert any("update_frequency" in loc for loc in error_locs)


    def test_create_tracker_unsupported_query_json_key(self):
        query_json = self._build_query_json(
            unknown_key="not allowed"
        )

        self._assert_create_tracker_query_json_error(
            name="Pytest Unsupported Query JSON Key",
            query_json=query_json,
            expected_detail="Unsupported query_json keys: ['unknown_key']"
        )


    def test_create_tracker_invalid_query_json_field_types(self):
        test_cases = [
            {
                "name": "Pytest Invalid Target Game Type",
                "query_json": self._build_query_json(
                    target_game="Elden Ring"
                ),
                "expected_detail": "target_game must be an object",
            },
            {
                "name": "Pytest Invalid Sources To Check Type",
                "query_json": self._build_query_json(
                    sources_to_check="mock"
                ),
                "expected_detail": "sources_to_check must be a list",
            },
            {
                "name": "Pytest Invalid Regions Type",
                "query_json": self._build_query_json(
                    regions="japan"
                ),
                "expected_detail": "regions must be a list",
            },
            {
                "name": "Pytest Invalid Genres Type",
                "query_json": self._build_query_json(
                    genres="Action RPG"
                ),
                "expected_detail": "genres must be a list",
            },
            {
                "name": "Pytest Invalid Platforms Type",
                "query_json": self._build_query_json(
                    platforms="PC"
                ),
                "expected_detail": "platforms must be a list",
            },
            {
                "name": "Pytest Invalid User Review Type",
                "query_json": self._build_query_json(
                    user_review="good game"
                ),
                "expected_detail": "user_review must be an object",
            },
            {
                "name": "Pytest Invalid Games Type",
                "query_json": self._build_query_json(
                    games="Elden Ring"
                ),
                "expected_detail": "games must be a list",
            },
            {
                "name": "Pytest Invalid Studios Type",
                "query_json": self._build_query_json(
                    studios="FromSoftware"
                ),
                "expected_detail": "studios must be a list",
            },
            {
                "name": "Pytest Invalid Is Indie Type",
                "query_json": self._build_query_json(
                    is_indie="false"
                ),
                "expected_detail": "is_indie must be a boolean",
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                self._assert_create_tracker_query_json_error(
                    name=case["name"],
                    query_json=case["query_json"],
                    expected_detail=case["expected_detail"]
                )

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

        assert response.status_code == expected_status_code, response.json()

        data = response.json()

        assert "detail" in data
        assert data.get("detail") == expected_detail

    def test_update_tracker_invalid_query_json_field_types(self):
        test_cases = [
            {
                "name": "Pytest Update Invalid Target Game Type",
                "query_json": self._build_query_json(
                    target_game="Elden Ring"
                ),
                "expected_detail": "target_game must be an object",
            },
            {
                "name": "Pytest Update Invalid Sources To Check Type",
                "query_json": self._build_query_json(
                    sources_to_check="mock"
                ),
                "expected_detail": "sources_to_check must be a list",
            },
            {
                "name": "Pytest Update Invalid Regions Type",
                "query_json": self._build_query_json(
                    regions="japan"
                ),
                "expected_detail": "regions must be a list",
            },
            {
                "name": "Pytest Update Invalid Genres Type",
                "query_json": self._build_query_json(
                    genres="Action RPG"
                ),
                "expected_detail": "genres must be a list",
            },
            {
                "name": "Pytest Update Invalid Platforms Type",
                "query_json": self._build_query_json(
                    platforms="PC"
                ),
                "expected_detail": "platforms must be a list",
            },
            {
                "name": "Pytest Update Invalid User Review Type",
                "query_json": self._build_query_json(
                    user_review="good game"
                ),
                "expected_detail": "user_review must be an object",
            },
            {
                "name": "Pytest Update Invalid Games Type",
                "query_json": self._build_query_json(
                    games="Elden Ring"
                ),
                "expected_detail": "games must be a list",
            },
            {
                "name": "Pytest Update Invalid Studios Type",
                "query_json": self._build_query_json(
                    studios="FromSoftware"
                ),
                "expected_detail": "studios must be a list",
            },
            {
                "name": "Pytest Update Invalid Is Indie Type",
                "query_json": self._build_query_json(
                    is_indie="false"
                ),
                "expected_detail": "is_indie must be a boolean",
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                self._assert_update_tracker_query_json_error(
                    query_json=case["query_json"],
                    expected_detail=case["expected_detail"]
                )

    def test_update_tracker_unsupported_query_json_key(self):
        query_json = self._build_query_json(
            unknown_key="not allowed"
        )

        self._assert_update_tracker_query_json_error(
            query_json=query_json,
            expected_detail="Unsupported query_json keys: ['unknown_key']"
        )
    
    def test_update_tracker_invalid_update_frequency(self):
        tracker_id, _ = self._create_tracker(
            name="Pytest Update Invalid Frequency Tracker"
        )

        update_payload = {
            "update_frequency": "hourly"
        }

        response = self.client.patch(
            "/v1/trackers/{0}".format(tracker_id),
            json=update_payload
        )

        assert response.status_code == 422, response.json()

        data = response.json()

        assert "detail" in data

        error_locs = [
            error.get("loc", [])
            for error in data.get("detail", [])
        ]

        assert any("update_frequency" in loc for loc in error_locs)
    
    def test_update_missing_tracker(self):
        update_payload = {
            "name": "Pytest Missing Updated Tracker",
            "update_frequency": "weekly",
            "is_active": False,
        }

        response = self.client.patch(
            "/v1/trackers/999999",
            json=update_payload
        )

        assert response.status_code == 404, response.json()

        data = response.json()

        assert "detail" in data
        assert data.get("detail") == "Tracker not found"

    def test_delete_missing_tracker(self):
        response = self.client.delete("/v1/trackers/999999")

        assert response.status_code == 404, response.json()

        data = response.json()

        assert "detail" in data
        assert data.get("detail") == "Tracker not found"

    def test_run_tracker_unsupported_source_records_failed_run(self):
        tracker_id, _ = self._create_tracker(
            name="Pytest Unsupported Source Tracker",
            source="steam"
        )

        response = self.client.post(
            "/v1/trackers/{0}/run".format(tracker_id)
        )

        assert response.status_code == 400, response.json()

        data = response.json()

        assert "detail" in data
        assert data.get("detail") == "Unsupported source: steam"

        runs_response = self.client.get(
            "/v1/trackers/{0}/runs".format(tracker_id)
        )

        assert runs_response.status_code == 200, runs_response.json()

        runs_data = runs_response.json()

        assert isinstance(runs_data, list)
        assert len(runs_data) >= 1

        latest_run = runs_data[0]

        assert latest_run.get("tracker_id") == tracker_id
        assert latest_run.get("status") == "failed"
        assert latest_run.get("error_message") == "Unsupported source: steam"

    def test_active_trackers_invalid_update_frequency_path(self):
        response = self.client.get("/v1/trackers/active/hourly")

        assert response.status_code == 400, response.json()

        data = response.json()

        assert "detail" in data
        assert data.get("detail") == "update_frequency must be one of ['daily', 'manual', 'weekly']"

if __name__ == "__main__":
    unittest.main()