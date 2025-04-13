# Login to Azure
az login

# Create resource group
az group create --name FastAPIDeployment --location eastus

# Create Azure File Share for Redis persistence
az storage account create --name fastapistorage123 --resource-group FastAPIDeployment --location eastus --sku Standard_LRS
az storage share create --name redisdata --account-name fastapistorage123

# Get storage key
STORAGE_KEY=$(az storage account keys list --account-name fastapistorage123 --resource-group FastAPIDeployment --query "[0].value" --output tsv)

# Deploy with docker-compose
az container create \
  --resource-group FastAPIDeployment \
  --name fastapi-celery-app \
  --image yourusername/fastapi-celery-app:latest \
  --dns-name-label fastapi-celery-app \
  --ports 8000 \
  --environment-variables REDIS_URL=redis://redis:6379/0 \
  --azure-file-volume-account-name fastapistorage123 \
  --azure-file-volume-account-key $STORAGE_KEY \
  --azure-file-volume-share-name redisdata \
  --azure-file-volume-mount-path /data