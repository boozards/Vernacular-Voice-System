import os
import uuid
import logging
import asyncio
from typing import Optional, Tuple
from shared.config import settings

logger = logging.getLogger("voicekart_s3")

# Local fallback directory inside workspace
LOCAL_STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".audio_storage"))
os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)



class S3AudioStorage:
    def __init__(self):
        self.bucket = settings.S3_BUCKET_NAME
        self.s3_client = None
        self._init_boto()

    def _init_boto(self):
        try:
            import boto3
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            # Ensure bucket exists
            try:
                self.s3_client.create_bucket(Bucket=self.bucket)
            except Exception:
                pass  # Bucket may already exist
        except Exception as e:
            logger.warning(f"S3/MinIO client init failed, using local storage fallback: {e}")
            self.s3_client = None

    async def upload_audio_bytes(self, audio_bytes: bytes, extension: str = "ogg") -> Tuple[str, str]:
        """
        Uploads audio bytes to S3/MinIO or local storage fallback.
        Returns: (s3_key_or_path, public_url)
        """
        file_id = str(uuid.uuid4())
        key = f"audio/{file_id}.{extension}"

        if self.s3_client:
            try:
                def _put_s3():
                    self.s3_client.put_object(
                        Bucket=self.bucket,
                        Key=key,
                        Body=audio_bytes,
                        ContentType=f"audio/{extension}",
                        Tagging="TTL=24h"
                    )
                await asyncio.to_thread(_put_s3)
                url = f"{settings.S3_ENDPOINT_URL}/{self.bucket}/{key}"
                return key, url
            except Exception as e:
                logger.error(f"Failed to upload to S3: {e}, falling back to local file")

        # Fallback to local storage
        local_path = os.path.join(LOCAL_STORAGE_DIR, f"{file_id}.{extension}")
        def _write_local():
            with open(local_path, "wb") as f:
                f.write(audio_bytes)
        await asyncio.to_thread(_write_local)

        local_url = f"file://{local_path}"
        return local_path, local_url

    async def download_audio_bytes(self, key_or_path: str) -> Optional[bytes]:
        """Downloads audio bytes from S3/MinIO or local file system."""
        if os.path.exists(key_or_path):
            def _read_local():
                with open(key_or_path, "rb") as f:
                    return f.read()
            return await asyncio.to_thread(_read_local)

        if self.s3_client:
            try:
                def _get_s3():
                    response = self.s3_client.get_object(Bucket=self.bucket, Key=key_or_path)
                    return response["Body"].read()
                return await asyncio.to_thread(_get_s3)
            except Exception as e:
                logger.error(f"Failed to download from S3 for key {key_or_path}: {e}")

        return None


s3_storage = S3AudioStorage()
