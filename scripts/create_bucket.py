"""Create S3 bucket for MLflow artifacts using boto3."""

import os
import boto3
from botocore.exceptions import ClientError

endpoint = os.environ["RUSTFS_ENDPOINT"]
access_key = os.environ["RUSTFS_ACCESS_KEY"]
secret_key = os.environ["RUSTFS_SECRET_KEY"]
bucket = os.environ.get("RUSTFS_BUCKET", "mlflow")

s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name="us-east-1",
)

try:
    s3.head_bucket(Bucket=bucket)
    print(f"Bucket '{bucket}' already exists.")
except ClientError:
    s3.create_bucket(Bucket=bucket)
    print(f"Bucket '{bucket}' created.")