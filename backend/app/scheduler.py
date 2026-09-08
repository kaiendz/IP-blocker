"""APScheduler wiring — in-process background jobs. Simplest ops footprint for
this scale (no Redis/Celery needed); each job opens/closes its own DB session."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.db.session import SessionLocal
from app.services import azure_publisher, detection, expiry, poller, threat_intel

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def _run_poll_all_devices() -> None:
    db = SessionLocal()
    try:
        poller.poll_all_devices(db)
    except Exception:
        logger.exception("poll_all_devices job failed")
    finally:
        db.close()


def _run_detection() -> None:
    db = SessionLocal()
    try:
        detection.run_detection(db)
    except Exception:
        logger.exception("run_detection job failed")
    finally:
        db.close()


def _run_threat_intel_refresh() -> None:
    db = SessionLocal()
    try:
        threat_intel.refresh_due_sources(db)
    except Exception:
        logger.exception("refresh_due_sources job failed")
    finally:
        db.close()


def _run_expiry_sweep() -> None:
    db = SessionLocal()
    try:
        expiry.expire_due_entries(db)
    except Exception:
        logger.exception("expire_due_entries job failed")
    finally:
        db.close()


def _run_azure_publish() -> None:
    db = SessionLocal()
    try:
        azure_publisher.publish(db)
    except Exception:
        logger.exception("azure publish job failed")
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(_run_poll_all_devices, "interval", minutes=settings.DEVICE_POLL_INTERVAL_MINUTES, id="poll_devices", max_instances=1)
    scheduler.add_job(_run_detection, "interval", minutes=settings.DETECTION_INTERVAL_MINUTES, id="detection", max_instances=1)
    scheduler.add_job(_run_threat_intel_refresh, "interval", minutes=15, id="threat_intel_refresh", max_instances=1)
    scheduler.add_job(_run_expiry_sweep, "interval", minutes=settings.EXPIRY_SWEEP_INTERVAL_MINUTES, id="expiry_sweep", max_instances=1)
    scheduler.add_job(_run_azure_publish, "interval", minutes=settings.AZURE_PUBLISH_INTERVAL_MINUTES, id="azure_publish", max_instances=1)
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
