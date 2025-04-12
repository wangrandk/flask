from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from redis import Redis
import json
import os
import hashlib
from typing import List, Dict
from dotenv import load_dotenv
from typing import Dict
load_dotenv()

app = FastAPI()
redis_client = Redis.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379/0"),
    decode_responses=True,
    socket_connect_timeout=5,
    retry_on_timeout=True
)

def get_payload_hash(payload: Dict) -> str:
    """Generate unique hash for payload to detect duplicates"""
    payload_str = f"{payload['latitude']}_{payload['longitude']}_{payload['timestamp']}"
    return hashlib.md5(payload_str.encode()).hexdigest()

@app.on_event("startup")
async def startup_event():
    """Initialize with empty deduplication set if not exists"""
    if not redis_client.exists("payload_hashes"):
        redis_client.sadd("payload_hashes", "init")  # Create set
        default_data = {
            "latitude": 55.752488,
            "longitude": 12.524214,
            "timestamp": "System Start"
        }
        redis_client.set("latest_entry", json.dumps(default_data))
        redis_client.lpush("history", json.dumps(default_data))
        redis_client.sadd("payload_hashes", get_payload_hash(default_data))

@app.get("/lastdata")
async def get_last_data() -> List[Dict]:
    """Get all data with duplicates removed"""
    try:
        # Get latest entry
        latest_entry = redis_client.get("latest_entry")
        latest = json.loads(latest_entry) if latest_entry else None
        
        # Get history (reverse to show newest first)
        history = [
            json.loads(h) 
            for h in redis_client.lrange("history", 0, -1) or []
        ][::-1]  # Reverse to show newest first
        
        # Deduplicate
        seen_hashes = set()
        deduped_data = []
        
        if latest:
            latest_hash = get_payload_hash(latest)
            if not redis_client.sismember("payload_hashes", latest_hash):
                deduped_data.append(latest)
                seen_hashes.add(latest_hash)
        
        for item in history:
            item_hash = get_payload_hash(item)
            if item_hash not in seen_hashes:
                deduped_data.append(item)
                seen_hashes.add(item_hash)
        
        return JSONResponse(deduped_data)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/map", response_class=HTMLResponse)
async def map_view():
    try:
        entry = redis_client.get("latest_entry")
        if not entry:
            return HTMLResponse("<h1>No data available</h1>", status_code=404)
        
        latest = json.loads(entry)
        history = redis_client.lrange("history", 0, 1000) or []
        
        markers = "\n".join([
            f"""L.marker([{json.loads(h)['latitude']}, {json.loads(h)['longitude']}])
            .bindPopup("Time: {json.loads(h)['timestamp']}<br>Lat: {json.loads(h)['latitude']}<br>Lon: {json.loads(h)['longitude']}")
            .addTo(map);"""
            for h in history
        ])
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bike Tracker Map</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
            <style>
                #map {{ height: 80vh; width: 100%; }}
            </style>
        </head>
        <body>
            <h1>Latest Position</h1>
            <div id="map"></div>
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <script>
                var map = L.map('map').setView([{latest['latitude']}, {latest['longitude']}], 15);
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                }}).addTo(map);
                {markers}
                L.circle([{latest['latitude']}, {latest['longitude']}], {{
                    color: 'red',
                    fillColor: '#f03',
                    fillOpacity: 0.5,
                    radius: 50
                }}).addTo(map);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(html)
    except Exception as e:
        return HTMLResponse(f"<h1>Error: {str(e)}</h1>", status_code=500)