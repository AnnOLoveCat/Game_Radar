import unittest

from fastapi.testclient import TestClient

from app.main import app


class TestApiBasic(unittest.TestCase):
    
    @classmethod
    # 先建立一個共用的 TestClient，避免每個測試都重建一次。
    def setUpClass(cls):
        cls.client = TestClient(app)

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


if __name__ == "__main__":
    unittest.main()