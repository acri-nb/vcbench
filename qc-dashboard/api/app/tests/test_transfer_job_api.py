import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app import job_service, models
from api.app.database import Base, get_db


class TransferJobApiTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "test.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False})
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.Session()

        from api.app.api_v1.endpoints import jobs

        app = FastAPI()
        app.include_router(jobs.router, prefix="/api/v1")

        def override_get_db():
            session = self.Session()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self._tmpdir.cleanup()

    def test_job_list_detail_events_summary_and_cancel(self):
        job = job_service.create_job(
            self.db,
            job_type=models.TransferJobType.AWS_IMPORT,
            subject_id="NA24143",
            phase=models.TransferJobPhase.DOWNLOAD,
            bytes_total=100,
        )
        job_service.append_event(
            self.db,
            job.id,
            "Download started",
            level=models.TransferEventLevel.INFO,
            phase=models.TransferJobPhase.DOWNLOAD,
        )
        job_service.update_progress(self.db, job.id, bytes_done=25, bytes_total=100, rate_bps=5)

        list_response = self.client.get("/api/v1/jobs")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()[0]["id"], job.id)

        detail_response = self.client.get(f"/api/v1/jobs/{job.id}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["subject_id"], "NA24143")
        self.assertEqual(detail_response.json()["bytes_done"], 25)

        events_response = self.client.get(f"/api/v1/jobs/{job.id}/events?since=1")
        self.assertEqual(events_response.status_code, 200)
        self.assertEqual(events_response.json()["total_events"], 2)
        self.assertEqual(len(events_response.json()["events"]), 1)
        self.assertEqual(events_response.json()["events"][0]["sequence"], 2)

        summary_response = self.client.get("/api/v1/jobs/summary")
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()["active_jobs"], 1)
        self.assertEqual(summary_response.json()["total_rate_bps"], 5)

        cancel_response = self.client.post(f"/api/v1/jobs/{job.id}/cancel")
        self.assertEqual(cancel_response.status_code, 200)
        self.assertTrue(cancel_response.json()["cancel_requested"])

        missing_response = self.client.get("/api/v1/jobs/missing")
        self.assertEqual(missing_response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
