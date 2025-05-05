# uvicorn consumer-service:app --port 8003 --reload
from fastapi import FastAPI
from confluent_kafka import Consumer
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
import time
import smtplib
import json
import threading
import time
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Get SMTP configuration from environment variables
SMTP_HOST = os.getenv('SMTP_HOST', 'mailhog')
SMTP_PORT = int(os.getenv('SMTP_PORT', '1025'))

# Kafka configuration
conf = {
    'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
    'security.protocol': os.getenv('KAFKA_SECURITY_PROTOCOL'),
    'sasl.mechanisms': os.getenv('KAFKA_SASL_MECHANISMS'),
    'sasl.username': os.getenv('KAFKA_SASL_USERNAME'),
    'sasl.password': os.getenv('KAFKA_SASL_PASSWORD'),
    'group.id': os.getenv('KAFKA_GROUP_ID', 'python-group-1'),
    'auto.offset.reset': os.getenv('KAFKA_AUTO_OFFSET_RESET', 'earliest')
}

consumer = Consumer(conf)
topic = os.getenv('KAFKA_TOPIC', 'email-notifs')

def send_email(to_email, subject, message):
    msg = MIMEMultipart()
    msg['From'] = 'notification@example.com'
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(message, 'plain'))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.send_message(msg)
        print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

def generate_iso8601_ns():
    # Get current time in total nanoseconds since epoch
    total_ns = time.time_ns()

    # Split into whole seconds and the sub‑second nanosecond part
    seconds = total_ns // 1_000_000_000
    nanos   = total_ns % 1_000_000_000

    # Build a UTC datetime from the whole seconds
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc)

    # Format date + time (up to seconds)
    base = dt.strftime('%Y-%m-%dT%H:%M:%S')

    # Format nanoseconds as 9 digits, then pad to 12 if desired:
    # here we append three zeros to get 12 fractional digits
    frac = f"{nanos:09d}000"

    # Combine and add Z suffix
    return f"{base}.{frac}Z"

def consume_messages():
    consumer.subscribe([topic])
    print(f"Consumer started. Listening to topic: {topic}")

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue

            try:
                data = json.loads(msg.value().decode('utf-8'))
                to_email = data.get('email')
                # subject = data.get('subject')
                subject = generate_iso8601_ns()
                message = data.get('message')

                if all([to_email, subject, message]):
                    send_email(to_email, subject, message)
                else:
                    print("Missing required email fields")
            except json.JSONDecodeError:
                print("Failed to decode message")
            except Exception as e:
                print(f"Error processing message: {str(e)}")

    except KeyboardInterrupt:
        print("Consumer stopped")
    finally:
        consumer.close()

@app.on_event("startup")
def startup_event():
    threading.Thread(target=consume_messages, daemon=True).start()