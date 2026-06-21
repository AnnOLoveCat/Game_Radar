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
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)

        if os.path.exists("test_scholar_radar.db"):
            os.remove("test_scholar_radar.db")

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


if __name__ == "__main__":
    unittest.main()