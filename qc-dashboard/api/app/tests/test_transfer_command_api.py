import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app import job_service, models, settings
from api.app.database import Base, get_db


class TransferCommandApiTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)
        self.engine = create_engine(
            f"sqlite:///{self.tmp_path / 'test.db'}",
            connect_args={"check_same_thread": False},
        )
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.Session()

        from api.app.api_v1.endpoints import runs, uploads

        self.original_upload_dir = uploads.UPLOAD_DIR
        self.original_lab_runs_dir = uploads.LAB_RUNS_DIR
        self.original_settings_upload_dir = settings.UPLOAD_DIR
        self.original_run_pipeline = runs.run_pipeline
        uploads.UPLOAD_DIR = self.tmp_path / "uploads"
        uploads.LAB_RUNS_DIR = self.tmp_path / "lab_runs"
        settings.UPLOAD_DIR = uploads.UPLOAD_DIR
        runs.run_pipeline = lambda *args, **kwargs: None

        app = FastAPI()
        app.include_router(uploads.router, prefix="/api/v1")
        app.include_router(runs.router, prefix="/api/v1")

        def override_get_db():
            session = self.Session()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        from api.app.api_v1.endpoints import runs, uploads

        uploads.UPLOAD_DIR = self.original_upload_dir
        uploads.LAB_RUNS_DIR = self.original_lab_runs_dir
        settings.UPLOAD_DIR = self.original_settings_upload_dir
        runs.run_pipeline = self.original_run_pipeline
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self._tmpdir.cleanup()

    def test_local_upload_returns_completed_transfer_job_when_auto_process_disabled(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("README.txt", "upload smoke test")
        payload = archive.getvalue()

        response = self.client.post(
            "/api/v1/upload/runs",
            data={"sample": "sample_run", "auto_process": "0", "benchmarking": "csv"},
            files={"file": ("sample_run.zip", payload, "application/zip")},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("job_id", body)
        self.assertEqual(body["bytes_received"], len(payload))

        job = job_service.get_job(self.db, body["job_id"])
        self.assertEqual(job.type, models.TransferJobType.UPLOAD_ZIP)
        self.assertEqual(job.status, models.TransferJobStatus.COMPLETED)
        self.assertEqual(job.phase, models.TransferJobPhase.COMPLETE)
        self.assertEqual(job.bytes_done, len(payload))

    def test_aws_import_without_auto_process_returns_queued_transfer_job(self):
        response = self.client.post(
            "/api/v1/upload/aws",
            json={
                "sample_id": "NA24143_Lib3_Rep1",
                "benchmarking": "csv,truvari",
                "auto_process": False,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("job_id", body)

        job = job_service.get_job(self.db, body["job_id"])
        self.assertEqual(job.type, models.TransferJobType.AWS_IMPORT)
        self.assertEqual(job.status, models.TransferJobStatus.QUEUED)
        self.assertEqual(job.phase, models.TransferJobPhase.DOWNLOAD)
        self.assertEqual(job.subject_id, "NA24143_Lib3_Rep1")

    def test_manual_benchmarking_returns_completed_pipeline_job(self):
        response = self.client.post(
            "/api/v1/runs/HG002_R001/benchmarking",
            params={"benchmarking": "csv,truvari"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("job_id", body)

        job = job_service.get_job(self.db, body["job_id"])
        self.assertEqual(job.type, models.TransferJobType.PIPELINE)
        self.assertEqual(job.status, models.TransferJobStatus.COMPLETED)
        self.assertEqual(job.phase, models.TransferJobPhase.COMPLETE)


if __name__ == "__main__":
    unittest.main()
