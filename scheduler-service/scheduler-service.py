# uvicorn scheduler-service:app --port 8001 --reload
from fastapi import FastAPI, Query, HTTPException
from typing import List
from pymongo import MongoClient
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError
from datetime import datetime, timezone
import requests
import uuid
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()
scheduler = BackgroundScheduler()
scheduler.start()

NOTIFICATION_SERVICE_URL=os.getenv('NOTIFICATION_SERVICE_URL')

def call_subscribers_api(job_id, category, subject, body):
    try:
        payload = {
            "category": category,
            "subject": subject,
            "message": body,
            "date_time": None  # explicitly set to null
        }

        # Note: email field is required by EmailRequest model,
        # but in this context it's filled dynamically inside /send-email
        # when iterating over subscribers. So we omit it here.
        response = requests.post(
            f"{NOTIFICATION_SERVICE_URL}/send-email/",
            json=payload
        )

        logger.info(f"[{datetime.now()}] Job {job_id} triggered /send-email/")
        logger.info(f"Response: {response.status_code} - {response.text}")

    finally:
        # Clean up job after it's run
        try:
            scheduler.remove_job(job_id)
        except JobLookupError:
            pass

# --------- Request model ---------
class ScheduleRequest(BaseModel):
    subject: str
    message: str
    category: str
    date_time: datetime


# --------- Endpoint to schedule the job ---------
@app.post("/schedule_notification")
def schedule_notification(req: ScheduleRequest):
    if req.date_time <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future")

    job_id = str(uuid.uuid4())

    scheduler.add_job(
        call_subscribers_api,
        trigger="date",
        run_date=req.date_time,
        args=[job_id, req.category, req.subject, req.message],  # Pass to job
        id=job_id,
        replace_existing=False
    )

    return {
        "message": "Notification job scheduled",
        "job_id": job_id,
        "scheduled_for": req.date_time.isoformat()
    }