from celery import Celery
import json
from redis import Redis, ConnectionError
from redis.retry import Retry
from redis.backoff import ExponentialBackoff
import os
import asyncio
import websockets  # Using async websockets library only
from dotenv import load_dotenv
load_dotenv()
from celery import Celery
import os


# Configure Celery with Azure Redis
app = Celery(
    'tasks',
    broker=f"rediss://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:6380/0?ssl_cert_reqs=none",
    backend=f"rediss://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:6380/1?ssl_cert_reqs=none"
)

# Redis client configuration (same as in main.py)
redis_client = Redis(
    host=os.getenv("REDIS_HOST"),
    port=6380,
    password=os.getenv("REDIS_PASSWORD"),
    ssl=True,
    ssl_cert_reqs=None,
    socket_timeout=10,
    retry_on_timeout=True
)

def hex_to_ascii(hex_string):
    try:
        return bytes.fromhex(hex_string).decode('utf-8')
    except:
        return hex_string

def process_message(message):
    """Process and validate incoming message"""
    try:
        if isinstance(message, str):
            data = json.loads(message)
            if 'data' in data:
                processed = hex_to_ascii(data['data'])
            else:
                processed = message
        else:
            processed = message.decode('utf-8')
        
        if ',' in processed:
            parts = [p.strip() for p in processed.split(',')]
            if len(parts) >= 3:
                return {
                    "latitude": float(parts[0]),
                    "longitude": float(parts[1]),
                    "timestamp": parts[2]
                }
        return None
    except Exception as e:
        print(f"Message processing error: {e}")
        return None

async def websocket_listener():
    """Standalone async websocket handler"""
    uri = "wss://iotnet.teracom.dk/app?token=vnoWVQAAABFpb3RuZXQudGVyYWNvbS5ka3_idG-uatIwbfwpA-5IsDE="
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({
            "command": "subscribe",
            "channels": ["gps_data"]
        }))
        
        while True:
            data = await websocket.recv()
            entry = process_message(data)  # Your existing message processor
            if entry:
                with redis_client.pipeline() as pipe:
                    pipe.set("latest_entry", json.dumps(entry))
                    pipe.lpush("history", json.dumps(entry))
                    pipe.ltrim("history", 0, 1000)
                    pipe.execute()

@app.task(bind=True, max_retries=3)
def start_websocket_task(self):
    """Synchronous Celery task wrapper"""
    try:
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the async function to completion
        loop.run_until_complete(websocket_listener())
        
    except Exception as e:
        print(f"WebSocket task failed: {str(e)}")
        self.retry(exc=e, countdown=5)
    finally:
        if 'loop' in locals():
            loop.close()