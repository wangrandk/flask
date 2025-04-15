# main.py (修复版)
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from redis import Redis
import json
import os
import websocket
from app.tasks import start_websocket_task
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

# Use Azure Redis environment variables
redis_host = os.getenv("REDIS_HOST")  # e.g., "bidockerapp-dev-azurecacheredis.redis.cache.windows.net"
redis_password = os.getenv("REDIS_PASSWORD")
redis_port = 6380  # Azure Redis SSL port

redis_client = Redis(
    host=redis_host,
    port=redis_port,
    password=redis_password,
    ssl=True,
    ssl_cert_reqs=None,
    socket_timeout=10,  # Add timeout
    retry_on_timeout=True  # Enable retry
)

@app.on_event("startup")
async def startup_event():
    # 初始化默认数据
    if not redis_client.exists("latest_entry") and not redis_client.exists("history"):
        default_data = {
            "latitude": 55.752488,
            "longitude": 12.524214,
            "timestamp": "System Start"
        }
        # redis_client.set("latest_entry", json.dumps(default_data))
        redis_client.lpush("history", json.dumps(default_data))
    
    # 启动WebSocket任务
    start_websocket_task.delay()

@app.get("/")
async def index():
    return {"status": "running", "service": "Smart Bike Tracker"}

@app.get("/data", response_class=HTMLResponse)
async def combined_view():
    try:
        # Get data from Redis
        latest_entry = redis_client.get("latest_entry")
        history = redis_client.lrange("history", 0, 1000) or []
        
        # Prepare data for JSON display
        all_data = []
        if latest_entry:
            all_data.append(json.loads(latest_entry))
        all_data.extend([json.loads(h) for h in history])
        
        # Prepare map markers
        latest = json.loads(latest_entry) if latest_entry else None
        markers = "\n".join([
            f"""L.marker([{json.loads(h)['latitude']}, {json.loads(h)['longitude']}])
            .bindPopup("Time: {json.loads(h)['timestamp']}<br>Lat: {json.loads(h)['latitude']}<br>Lon: {json.loads(h)['longitude']}")
            .addTo(map);"""
            for h in history
        ]) if latest else ""
        
        # Create the combined HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>🚴 Bike Tracker - Combined View</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
            <style>
                #map {{ height: 60vh; width: 100%; }}
                .data-container {{ 
                    margin: 20px;
                    padding: 20px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    background-color: #f9f9f9;
                }}
                pre {{ 
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    background-color: #f0f0f0;
                    padding: 10px;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <h1>🚴Bike Tracker - Combined View</h1>
            
            <h2>Map View</h2>
            <div id="map"></div>
            
            <div class="data-container">
                <h2>Location Data</h2>
                <pre>{json.dumps(all_data, indent=2)}</pre>
            </div>
            
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
    
