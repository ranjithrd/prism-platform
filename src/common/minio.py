import io
import logging
import os
from datetime import timedelta
from typing import Optional

from minio.error import S3Error

import minio

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class MinioHelper:
    """
    A helper class to interact with a Minio server, providing methods for
    uploading, downloading, and caching files.
    """

    DEFAULT_BUCKET = "traces"

    def __init__(self, host: str, access_key: str, secret_key: str, cache_dir: str = ".cache"):
        """
        Initializes the Minio client.

        Args:
            host (str): The Minio server endpoint (e.g., "localhost:9000").
            access_key (str): The access key for the Minio server.
            secret_key (str): The secret key for the Minio server.
            cache_dir (str): The local directory to use for caching downloaded files.
        """
        if not all([host, access_key, secret_key]):
            raise ValueError("Minio host, access key, and secret key must be provided.")

        self.client = minio.Minio(
            host,
            access_key=access_key,
            secret_key=secret_key,
            secure=False,
            # The client automatically handles http/https based on the host string.
            # If your host does not start with https://, secure will be False.
        )
        self.cache_dir = cache_dir
        logging.info(f"MinioHelper initialized for host: {host}")
        self._ensure_bucket_exists(self.DEFAULT_BUCKET)

    def _ensure_bucket_exists(self, bucket_name: str):
        """
        Checks if a bucket exists and creates it if it does not.

        Args:
            bucket_name (str): The name of the bucket.
        """
        try:
            found = self.client.bucket_exists(bucket_name)
            if not found:
                self.client.make_bucket(bucket_name)
                logging.info(f"Bucket '{bucket_name}' created.")
            else:
                logging.info(f"Bucket '{bucket_name}' already exists.")
        except S3Error as exc:
            logging.error(f"Error ensuring bucket '{bucket_name}' exists: {exc}")
            raise

    def upload_bytes(self, bucket_name: str, object_name: str, data: bytes):
        """
        Uploads a bytes object to a Minio bucket.

        Args:
            bucket_name (str): The name of the target bucket.
            object_name (str): The name for the object in the bucket.
            data (bytes): The bytes content to upload.
        """
        self._ensure_bucket_exists(bucket_name)
        try:
            result = self.client.put_object(
                bucket_name,
                object_name,
                io.BytesIO(data),
                len(data),
                content_type='application/octet-stream'
            )
            logging.info(
                f"Successfully uploaded {object_name} to bucket {bucket_name}. ETag: {result.etag}"
            )
        except S3Error as exc:
            logging.error(f"Error uploading bytes to {bucket_name}/{object_name}: {exc}")
            raise

    def download_bytes(self, bucket_name: str, object_name: str) -> Optional[bytes]:
        """
        Downloads an object from a Minio bucket as bytes.

        Args:
            bucket_name (str): The name of the bucket.
            object_name (str): The name of the object to download.

        Returns:
            Optional[bytes]: The content of the object as bytes, or None if an error occurs.
        """
        try:
            response = self.client.get_object(bucket_name, object_name)
            content = response.read()
            logging.info(f"Successfully downloaded {object_name} from bucket {bucket_name}.")
            return content
        except S3Error as exc:
            logging.error(f"Error downloading bytes from {bucket_name}/{object_name}: {exc}")
            return None
        finally:
            # Ensure the connection is released
            if 'response' in locals() and response:
                response.close()
                response.release_conn()

    def download_cached(self, bucket_name: str, object_name: str) -> Optional[str]:
        """
        Downloads an object from Minio, caching it locally to avoid repeated downloads.

        Args:
            bucket_name (str): The name of the bucket.
            object_name (str): The name of the object.

        Returns:
            Optional[str]: The local file path to the cached object, or None on error.
        """
        # Construct a safe local path inside the cache directory
        # Using the bucket name as a subfolder to prevent name collisions
        local_dir = os.path.join(self.cache_dir, bucket_name)
        local_filepath = os.path.join(local_dir, object_name)

        # If the file already exists in the cache, return its path
        if os.path.exists(local_filepath):
            logging.info(f"'{object_name}' found in local cache: {local_filepath}")
            return local_filepath

        logging.info(f"'{object_name}' not in cache. Downloading from Minio...")

        # Create the local directory if it doesn't exist
        os.makedirs(local_dir, exist_ok=True)

        # Download the file from Minio to the cache path
        try:
            self.client.fget_object(bucket_name, object_name, local_filepath)
            logging.info(f"Downloaded and cached '{object_name}' to {local_filepath}")
            return local_filepath
        except S3Error as exc:
            logging.error(f"Failed to download {object_name} from {bucket_name}: {exc}")
            # Clean up partially downloaded file if it exists
            if os.path.exists(local_filepath):
                os.remove(local_filepath)
            return None

    def get_presigned_url(self, bucket_name: str, object_name: str, expiry_seconds: int = 3600) -> Optional[str]:
        """
        Generates a presigned URL for accessing an object in Minio without authentication.

        Args:
            bucket_name (str): The name of the bucket.
            object_name (str): The name of the object.
            expiry_seconds (int): Time in seconds for the presigned URL to remain valid.

        Returns:
            Optional[str]: The presigned URL, or None on error.
        """
        try:
            # Convert the integer seconds into a timedelta object
            url = self.client.presigned_get_object(
                bucket_name,
                object_name,
                expires=timedelta(seconds=expiry_seconds)
            )
            logging.info(f"Generated presigned URL for {object_name} in bucket {bucket_name}.")
            return url
        except S3Error as exc:
            logging.error(f"Error generating presigned URL for {bucket_name}/{object_name}: {exc}")
            return None


# --- Global Instance and Initializer ---

# This will hold the singleton instance of our helper class.
minio_helper_client: Optional[MinioHelper] = None


def initialize_minio_client():
    """
    Initializes the global Minio client from environment variables.
    This should be called once when your application starts.
    """
    global minio_helper_client
    logging.info("Initializing Minio client...")
    if minio_helper_client is None:
        try:
            minio_helper_client = MinioHelper(
                host=os.getenv("MINIO_HOST"),
                access_key=os.getenv("MINIO_ACCESS_KEY"),
                secret_key=os.getenv("MINIO_SECRET_KEY"),
            )
            logging.info("Minio client initialized successfully.")
        except ValueError as e:
            logging.error(f"Failed to initialize Minio client: {e}")
            # Depending on your app's needs, you might want to exit or handle this differently.
            minio_helper_client = None


def get_minio_client() -> Optional[MinioHelper]:
    """
    Returns the global Minio client instance.
    Ideal for use with dependency injection systems like FastAPI's Depends().

    Example with FastAPI:
    from fastapi import Depends, FastAPI

    app = FastAPI()

    @app.on_event("startup")
    async def startup_event():
        initialize_minio_client()

    @app.post("/upload")
    async def upload_data(minio_client: MinioHelper = Depends(get_minio_client)):
        # ... use minio_client here ...
        pass
    """
    return minio_helper_client
