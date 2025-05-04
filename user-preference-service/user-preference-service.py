# uvicorn user-preference-service:app --port 8000 --reload
from fastapi import FastAPI, Query, HTTPException
from typing import List
from pymongo import MongoClient
from pydantic import BaseModel
from urllib.parse import quote_plus
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()

username = quote_plus("pranav0706")
password = quote_plus("Pokemon123")

uri = f"mongodb+srv://{username}:{password}@cluster0.j5ickkr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)
db = client["user-preferences"]
users_collection = db["preferences"]

# Response Model
class UserChannels(BaseModel):
    user_id: str
    channels: List[str]

@app.get("/subscribers", response_model=List[UserChannels])
def get_subscribed_users(category: str = Query(...)):

    query = {f"categories.{category}": True}
    users = users_collection.find(query)

    result = []
    for user in users:
        preferred_channels = [
            channel for channel, value in user.get("channels", {}).items() if value
        ]
        result.append(UserChannels(
            user_id=user["_id"],
            channels=preferred_channels
        ))

    return result