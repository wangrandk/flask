docker-compose up


1. venv (required for your app)
# python -m venv venv       # Create a virtual environment
# source venv/bin/activate  # Activate it (Linux/Mac)
# OR
.\.venv\Scripts\activate  

2. Start Redis (required for your app)
# Your app uses Redis for storing data. Start the Redis server in a new terminal window:
.\redis-server
redis-server C:\MyGitHub\flask\redis.conf

3. Start Celery (for WebSocket tasks)
# In another terminal (with the virtualenv activated), run:
celery -A tasks worker --loglevel=info 


4. Run the FastAPI app with Uvicorn
uvicorn main:app --reload     

5. Access the application
Your API will be available at:
http://127.0.0.1:8000

The /lastdata endpoint:
http://127.0.0.1:8000/lastdata

The map view:
http://127.0.0.1:8000/map

celery -A tasks inspect ping  
.\redis-cli -h localhost -p 6379 ping  
.\redis-cli GET latest_data       
.\redis-cli.exe ping  


docker-compose exec redis ls -la /data

docker volume ls  # Should show your volume if using Option 1
docker-compose exec redis redis-cli ping  # Should return PONG

KEYS *
GET latest_data



# docker push
docker tag redis:7-alpine philipwang/redis:7-alpine
docker tag flask-app:latest philipwang/flask-app:latest
docker tag flask-celery:latest philipwang/flask-celery:latest

docker push philipwang/redis:7-alpine 
docker push philipwang/flask-celery:latest
docker push philipwang/flask-app:latest 