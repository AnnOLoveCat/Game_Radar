import os
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import get_db
from app.models import Base


TEST_DB_URL = "sqlite:///./test_game_radar.db"

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

    if os.path.exists("test_game_radar.db"):
        os.remove("test_game_radar.db")

    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_create_tracker(self):
        payload = {
            "name": "Pytest Japan Tracker",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "daily",
            "is_active": True,
        }

        response = self.client.post("/v1/trackers", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(data.get("name"), "Pytest Japan Tracker")
        self.assertEqual(data.get("source"), "mock")
        self.assertEqual(data.get("update_frequency"), "daily")
        self.assertTrue(data.get("is_active"))

    def test_list_trackers(self):
        response = self.client.get("/v1/trackers")

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_dashboard_summary(self):
        response = self.client.get("/v1/dashboard/summary")

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn("tracker_count", data)
        self.assertIn("active_tracker_count", data)
        self.assertIn("game_count", data)
        self.assertIn("run_count", data)

    def test_run_tracker(self):
        payload = {
            "name": "Pytest Run Tracker",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "daily",
            "is_active": True,
        }

        create_response = self.client.post("/v1/trackers", json=payload)
        self.assertEqual(create_response.status_code, 200)

        tracker_data = create_response.json()
        tracker_id = tracker_data.get("id")

        self.assertIsNotNone(tracker_id)

        run_response = self.client.post("/v1/trackers/{0}/run".format(tracker_id))
        self.assertEqual(run_response.status_code, 200)

        run_data = run_response.json()

        self.assertEqual(run_data.get("tracker_id"), tracker_id)
        self.assertIn("inserted_games", run_data)
        self.assertIn("matched_games", run_data)

    def test_tracker_summary(self):
        payload = {
            "name": "Pytest Summary Tracker",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "daily",
            "is_active": True,
        }

        create_response = self.client.post("/v1/trackers", json=payload)
        self.assertEqual(create_response.status_code, 200)

        tracker_data = create_response.json()
        tracker_id = tracker_data.get("id")

        self.assertIsNotNone(tracker_id)

        run_response = self.client.post("/v1/trackers/{0}/run".format(tracker_id))
        self.assertEqual(run_response.status_code, 200)

        summary_response = self.client.get("/v1/trackers/{0}/summary".format(tracker_id))
        self.assertEqual(summary_response.status_code, 200)

        summary_data = summary_response.json()

        self.assertEqual(summary_data.get("tracker_id"), tracker_id)
        self.assertEqual(summary_data.get("name"), "Pytest Summary Tracker")
        self.assertIn("matched_games_count", summary_data)
        self.assertIn("latest_run", summary_data)

    def test_dashboard_recent_runs(self):
        payload = {
            "name": "Pytest Recent Runs Tracker",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "daily",
            "is_active": True,
        }

        create_response = self.client.post("/v1/trackers", json=payload)
        self.assertEqual(create_response.status_code, 200)

        tracker_data = create_response.json()
        tracker_id = tracker_data.get("id")

        self.assertIsNotNone(tracker_id)

        run_response = self.client.post("/v1/trackers/{0}/run".format(tracker_id))
        self.assertEqual(run_response.status_code, 200)

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
        payload = {
            "name": "Pytest Recent Games Tracker",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "daily",
            "is_active": True,
        }

        create_response = self.client.post("/v1/trackers", json=payload)
        self.assertEqual(create_response.status_code, 200)

        tracker_data = create_response.json()
        tracker_id = tracker_data.get("id")

        self.assertIsNotNone(tracker_id)

        run_response = self.client.post("/v1/trackers/{0}/run".format(tracker_id))
        self.assertEqual(run_response.status_code, 200)

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
        payload = {
            "name": "Pytest Active Tracker",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "daily",
            "is_active": True,
        }

        create_response = self.client.post("/v1/trackers", json=payload)
        self.assertEqual(create_response.status_code, 200)

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

    def test_active_trackers_by_frequency(self):
        payload_daily = {
            "name": "Pytest Daily Tracker",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "daily",
            "is_active": True,
        }

        payload_weekly = {
            "name": "Pytest Weekly Tracker",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "weekly",
            "is_active": True,
        }

        response_daily_create = self.client.post("/v1/trackers", json=payload_daily)
        self.assertEqual(response_daily_create.status_code, 200)

        response_weekly_create = self.client.post("/v1/trackers", json=payload_weekly)
        self.assertEqual(response_weekly_create.status_code, 200)

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
        payload_daily_1 = {
            "name": "Pytest Batch Daily Tracker 1",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "daily",
            "is_active": True,
        }

        payload_daily_2 = {
            "name": "Pytest Batch Daily Tracker 2",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "daily",
            "is_active": True,
        }

        payload_weekly = {
            "name": "Pytest Batch Weekly Tracker",
            "source": "mock",
        "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
        "update_frequency": "weekly",
        "is_active": True,
        }

        response_1 = self.client.post("/v1/trackers", json=payload_daily_1)
        self.assertEqual(response_1.status_code, 200)

        response_2 = self.client.post("/v1/trackers", json=payload_daily_2)
        self.assertEqual(response_2.status_code, 200)

        response_3 = self.client.post("/v1/trackers", json=payload_weekly)
        self.assertEqual(response_3.status_code, 200)

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

    def test_tracker_runs_endpoint(self):
        payload = {
            "name": "Pytest Tracker Runs Endpoint",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "daily",
            "is_active": True,
        }

        create_response = self.client.post("/v1/trackers", json=payload)
        self.assertEqual(create_response.status_code, 200)

        tracker_data = create_response.json()
        tracker_id = tracker_data.get("id")

        self.assertIsNotNone(tracker_id)

        run_response = self.client.post("/v1/trackers/{0}/run".format(tracker_id))
        self.assertEqual(run_response.status_code, 200)

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
        payload = {
            "name": "Pytest Tracker Games Endpoint",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "daily",
            "is_active": True,
        }

        create_response = self.client.post("/v1/trackers", json=payload)
        self.assertEqual(create_response.status_code, 200)

        tracker_data = create_response.json()
        tracker_id = tracker_data.get("id")

        self.assertIsNotNone(tracker_id)

        run_response = self.client.post("/v1/trackers/{0}/run".format(tracker_id))
        self.assertEqual(run_response.status_code, 200)

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

    def test_update_tracker(self):
        payload = {
            "name": "Pytest Update Tracker",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "daily",
            "is_active": True,
        }

        create_response = self.client.post("/v1/trackers", json=payload)
        self.assertEqual(create_response.status_code, 200)

        tracker_data = create_response.json()
        tracker_id = tracker_data.get("id")

        self.assertIsNotNone(tracker_id)

        update_payload = {
            "name": "Pytest Updated Tracker",
            "update_frequency": "weekly",
            "is_active": False,
        }

        update_response = self.client.patch("/v1/trackers/{0}".format(tracker_id), json=update_payload)
        self.assertEqual(update_response.status_code, 200)

        updated_data = update_response.json()

        self.assertEqual(updated_data.get("id"), tracker_id)
        self.assertEqual(updated_data.get("name"), "Pytest Updated Tracker")
        self.assertEqual(updated_data.get("update_frequency"), "weekly")
        self.assertEqual(updated_data.get("is_active"), False)

    def test_delete_tracker(self):
        payload = {
            "name": "Pytest Delete Tracker",
            "source": "mock",
            "query_json": "{\"regions\":[\"japan\"],\"games\":[],\"is_indie\":false,\"studios\":[]}",
            "update_frequency": "daily",
            "is_active": True,
        }

        create_response = self.client.post("/v1/trackers", json=payload)
        self.assertEqual(create_response.status_code, 200)

        tracker_data = create_response.json()
        tracker_id = tracker_data.get("id")

        self.assertIsNotNone(tracker_id)

        delete_response = self.client.delete("/v1/trackers/{0}".format(tracker_id))
        self.assertEqual(delete_response.status_code, 200)

        get_response = self.client.get("/v1/trackers/{0}".format(tracker_id))
        self.assertEqual(get_response.status_code, 404)

if __name__ == "__main__":
    unittest.main()