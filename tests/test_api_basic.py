import os
import unittest

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
    # Helper Methods
    # =========================

    def _build_tracker_payload(
        self,
        name,
        update_frequency="daily",
        is_active=True,
        source="mock"
    ):
        return {
            "name": name,
            "source": source,
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": update_frequency,
            "is_active": is_active,
        }

    def _create_tracker(
        self,
        name,
        update_frequency="daily",
        is_active=True,
        source="mock"
    ):
        payload = self._build_tracker_payload(
            name=name,
            update_frequency=update_frequency,
            is_active=is_active,
            source=source
        )

        response = self.client.post("/v1/trackers", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        tracker_id = data.get("id")

        self.assertIsNotNone(tracker_id)

        return tracker_id, data

    def _run_tracker_once(self, tracker_id):
        response = self.client.post("/v1/trackers/{0}/run".format(tracker_id))
        self.assertEqual(response.status_code, 200)

        return response.json()

    # =========================
    # Basic API Tests
    # =========================

    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_create_tracker(self):
        tracker_id, data = self._create_tracker("Pytest Japan Tracker")

        self.assertIsNotNone(tracker_id)
        self.assertEqual(data.get("name"), "Pytest Japan Tracker")
        self.assertEqual(data.get("source"), "mock")
        self.assertEqual(data.get("update_frequency"), "daily")
        self.assertTrue(data.get("is_active"))

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
        self.assertEqual(update_response.status_code, 200)

        updated_data = update_response.json()

        self.assertEqual(updated_data.get("id"), tracker_id)
        self.assertEqual(updated_data.get("name"), "Pytest Updated Tracker")
        self.assertEqual(updated_data.get("update_frequency"), "weekly")
        self.assertEqual(updated_data.get("is_active"), False)

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
        self.assertEqual(summary_response.status_code, 200)

        summary_data = summary_response.json()

        self.assertEqual(summary_data.get("tracker_id"), tracker_id)
        self.assertEqual(summary_data.get("name"), "Pytest Summary Tracker")
        self.assertIn("matched_games_count", summary_data)
        self.assertIn("latest_run", summary_data)

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
        payload = {
            "name": "Pytest Invalid Query JSON",
            "source": "mock",
            "query_json": "{invalid_json}",
            "update_frequency": "daily",
            "is_active": True,
        }

        response = self.client.post("/v1/trackers", json=payload)

        self.assertEqual(response.status_code, 400)

        data = response.json()
        self.assertIn("detail", data)
        self.assertEqual(data.get("detail"), "Invalid query_json format")

    def test_create_tracker_invalid_update_frequency(self):
        payload = {
            "name": "Pytest Invalid Frequency",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "hourly",
            "is_active": True,
        }

        response = self.client.post("/v1/trackers", json=payload)

        self.assertEqual(response.status_code, 422)

        data = response.json()
        self.assertIn("detail", data)

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


if __name__ == "__main__":
    unittest.main()