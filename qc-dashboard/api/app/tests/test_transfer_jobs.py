import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.app import models
from api.app.database import Base


class TransferJobServiceTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "test.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self._tmpdir.cleanup()

    def test_create_job_append_event_and_update_progress(self):
        from api.app import job_service

        job = job_service.create_job(
            self.db,
            job_type=models.TransferJobType.UPLOAD_ZIP,
            subject_id="sample_run.zip",
            phase=models.TransferJobPhase.UPLOAD,
            source_uri="browser://sample_run.zip",
            bytes_total=200,
        )

        event = job_service.append_event(
            self.db,
            job.id,
            "Started upload",
            level=models.TransferEventLevel.INFO,
            phase=models.TransferJobPhase.UPLOAD,
        )
        updated = job_service.update_progress(self.db, job.id, bytes_done=50, bytes_total=200)

        self.assertEqual(job.type, models.TransferJobType.UPLOAD_ZIP)
        self.assertEqual(job.status, models.TransferJobStatus.RUNNING)
        self.assertEqual(event.sequence, 1)
        self.assertEqual(updated.bytes_done, 50)
        self.assertEqual(updated.bytes_total, 200)

        events = job_service.list_events(self.db, job.id)
        self.assertEqual([item.sequence for item in events], [1, 2])
        self.assertEqual(events[-1].level, models.TransferEventLevel.PROGRESS)

    def test_complete_and_fail_jobs_update_summary(self):
        from api.app import job_service

        running = job_service.create_job(
            self.db,
            job_type=models.TransferJobType.AWS_IMPORT,
            subject_id="NA24143",
            phase=models.TransferJobPhase.DOWNLOAD,
            bytes_total=1000,
        )
        job_service.update_progress(self.db, running.id, bytes_done=400, rate_bps=100)

        completed = job_service.create_job(
            self.db,
            job_type=models.TransferJobType.PIPELINE,
            subject_id="HG002_R001",
            phase=models.TransferJobPhase.PROCESS,
        )
        job_service.complete_job(self.db, completed.id, "Pipeline completed")

        failed = job_service.create_job(
            self.db,
            job_type=models.TransferJobType.UPLOAD_ZIP,
            subject_id="bad.zip",
            phase=models.TransferJobPhase.VALIDATE,
        )
        job_service.fail_job(self.db, failed.id, "Invalid ZIP", error_code="invalid_zip")

        summary = job_service.get_job_summary(self.db, data_dir=Path(self._tmpdir.name))

        self.assertEqual(summary["active_jobs"], 1)
        self.assertEqual(summary["queued_jobs"], 0)
        self.assertEqual(summary["failed_24h"], 1)
        self.assertEqual(summary["total_rate_bps"], 100)
        self.assertGreater(summary["disk_free_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
