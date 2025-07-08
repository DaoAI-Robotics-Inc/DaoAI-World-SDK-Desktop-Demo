import io
import logging
import os

import boto3

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = "demo"

logger = logging.getLogger(__name__)

client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    verify=False,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
)


def save_image(
    camera_id: int,
    timestamp: int,
    image_data: bytes,
):
    extra_args = {"ContentType": "image/jpeg"}
    with io.BytesIO(image_data) as fp:
        client.upload_fileobj(
            fp,
            Bucket=S3_BUCKET,
            Key=f"camera/{camera_id}/frame/{timestamp}/image.jpg",
            ExtraArgs=extra_args,
        )
