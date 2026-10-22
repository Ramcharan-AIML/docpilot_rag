# MLflow tracking server for DocPilot (step 3.1b, D-051).
# The official image has MLflow only; storing artifacts in S3 (SeaweedFS locally, Amazon S3
# on AWS) needs boto3 on the SERVER. The "-full" image has it too, but also Azure, gateway
# and GenAI extras we do not use, so we add just boto3 on top of the small image.
# Base checked 2026-10-21 on ghcr.io: v3.17.1 = our pinned mlflow, amd64 + arm64.
FROM ghcr.io/mlflow/mlflow:v3.17.1
RUN pip install --no-cache-dir boto3==1.43.116
