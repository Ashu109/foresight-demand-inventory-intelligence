# Cloud Deployment

## Environment variables

Set the following variables in your cloud platform:

- `DATA_ROOT=/mnt/data`
- `PROCESSED_DATA_DIR=/mnt/data/processed`
- `RAW_DATA_DIR=/mnt/data/raw`
- `LOG_LEVEL=INFO`
- `STREAMLIT_SERVER_PORT=8501`

## Suggested deployment targets

- Azure Container Apps
- AWS Elastic Container Service (ECS)
- Google Cloud Run
- Railway / Render / Fly.io

## Persistent storage

Mount a persistent volume or object storage-backed directory at `/mnt/data`.
For production, prefer a managed storage service for `processed/` and `raw/` data.

## Example container run

```powershell
docker run --rm -p 8501:8501 -e DATA_ROOT=/mnt/data -e LOG_LEVEL=INFO -v ${PWD}\data:/mnt/data:rw forsight-dashboard:local
```
