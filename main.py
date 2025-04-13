# main.py (修复版)
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from redis import Redis
import json
import os
import websocket
from tasks import start_websocket_task
from dotenv import load_dotenv
import folium
import pandas as pd
load_dotenv()

app = FastAPI()
# In main.py, update Redis connection:
redis_client = Redis.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379/0"),  # Note 'redis' hostname
    decode_responses=True,
    socket_connect_timeout=5,
    retry_on_timeout=True,
    health_check_interval=30  # Better for persistent connections
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
    
# @app.get("/dashboard", response_class=HTMLResponse)
# async def dashboard():
#     try:
#         # 1. Get Redis data
#         history = redis_client.lrange("history", 0, 1000) or []
#         if not history:
#             return HTMLResponse("<div class='alert alert-info'>No data available</div>")
        
#         data = [json.loads(h) for h in history]
        
#         # 2. Create simple map (Folium)
#         m = folium.Map(
#             location=[data[0]['latitude'], data[0]['longitude']],
#             zoom_start=13,
#             tiles="cartodbpositron",  # Lightweight tiles for mobile
#             control_scale=True
#         )
        
#         # Add simple markers
#         for point in data[-50:]:  # Show last 50 points for mobile performance
#             folium.CircleMarker(
#                 [point['latitude'], point['longitude']],
#                 radius=4,
#                 color='red',
#                 fill=True,
#                 popup=f"{point['timestamp']}"
#             ).add_to(m)
        
#         # 3. Create mobile-friendly table (Pandas)
#         df = pd.DataFrame(data)[-20:]  # Last 20 entries for mobile
#         table_html = df.to_html(
#             classes="table table-sm table-striped",
#             index=False
#         )
        
#         # 4. Mobile-optimized HTML
#         html = f"""
#         <!DOCTYPE html>
#         <html>
#         <head>
#             <meta name="viewport" content="width=device-width, initial-scale=1">
#             <title>Bike Tracker</title>
#             <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
#             <style>
#                 /* Mobile-first responsive layout */
#                 .map-container {{
#                     height: 50vh;
#                     width: 100%;
#                     margin-bottom: 10px;
#                 }}
#                 .table-container {{
#                     max-height: 40vh;
#                     overflow-y: auto;
#                     -webkit-overflow-scrolling: touch; /* Smooth iOS scrolling */
#                 }}
#                 /* Better table rendering on mobile */
#                 table {{
#                     font-size: 14px;
#                     width: 100% !important;
#                 }}
#                 /* No horizontal scroll on mobile */
#                 body {{
#                     overflow-x: hidden;
#                     padding: 10px;
#                 }}
#             </style>
#         </head>
#         <body>
#             <div class="container-fluid">
#                 <h5 class="text-center mb-3">🚴 Live Bike Tracker</h5>
#                 <div class="map-container border rounded">
#                     {m._repr_html_()}
#                 </div>
#                 <div class="table-container border rounded p-2">
#                     {table_html}
#                 </div>
#             </div>
#             <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
#         </body>
#         </html>
#         """
#         return HTMLResponse(html)
    
#     except Exception as e:
#         return HTMLResponse(f"""
#             <div class="alert alert-danger m-2">
#                 Error: {str(e)}
#             </div>
#         """)