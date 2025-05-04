# uvicorn producer-service:app --port 8002 --reload
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from confluent_kafka import Producer
from datetime import datetime, timezone
import json
import requests
import os

app = FastAPI()

# Kafka Config
conf = {
    'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
    'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
    'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
    'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
    'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
}

producer = Producer(conf)
TOPIC = os.getenv('KAFKA_TOPIC')

# Service URLs
USER_PREFERENCE_SERVICE_URL = os.getenv('USER_PREFERENCE_SERVICE_URL')
SCHEDULER_SERVICE_URL = os.getenv('SCHEDULER_SERVICE_URL')

# Request Model
class EmailRequest(BaseModel):
    subject: str
    message: str
    category: str
    date_time: datetime | None = None  # Optional

@app.post("/send-email/")
def send_email(request: EmailRequest):
    # Check if future date is valid (if provided)
    if request.date_time:
        if request.date_time <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="date_time must be in the future")

        # Schedule the job
        try:
            response = requests.post(f"{SCHEDULER_SERVICE_URL}/schedule_notification", json={
                "date_time": request.date_time.isoformat(),
                "category": request.category,
                "subject": request.subject,
                "message": request.message
            })

            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)

            return {
                "status": "Notification job scheduled",
                "job_id": response.json().get("job_id")
            }

        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=f"Failed to schedule job: {str(e)}")

    # If no date_time, send immediately to current subscribers
    try:
        subscriber_response = requests.get(f"{USER_PREFERENCE_SERVICE_URL}/subscribers", params={"category": request.category})
        if subscriber_response.status_code != 200:
            raise HTTPException(status_code=subscriber_response.status_code, detail="Failed to fetch subscribers")

        subscribers = subscriber_response.json()

        for subscriber in subscribers:
            data = {
                "email": subscriber["user_id"],  # Assuming user_id is email
                "subject": request.subject,
                "message": request.message
            }
            producer.produce(TOPIC, json.dumps(data).encode('utf-8'))

        producer.flush()
        return {"status": f"Messages sent to {len(subscribers)} subscribers"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
