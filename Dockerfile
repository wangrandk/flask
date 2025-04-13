# Dockerfile (for both app and celery)
FROM python:3.9

WORKDIR /app

# Install ping and other network tools
RUN apt-get update && apt-get install -y iputils-ping net-tools && rm -rf /var/lib/apt/lists/*


# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]