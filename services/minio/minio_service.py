from minio import Minio
from minio.error import S3Error
from datetime import timedelta
import io

class MinioConfig:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket_name: str, port: int = 443):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.port = port

class MinioManager:
    def __init__(self, config: MinioConfig):
        self.config = config
        self.client = self._initialize_client()
    def _initialize_client(self):
        from minio import Minio
        return Minio(
            endpoint=self.config.endpoint,
            access_key=self.config.access_key,
            secret_key=self.config.secret_key,
            secure=self.config.port == 443
        )
    def get_client(self):
        return self.client
    def get_bucket_name(self):
        return self.config.bucket_name
    
    def upload_file(self, file_path: str, object_name: str):
        try:
            self.client.fput_object(
                bucket_name=self.config.bucket_name,
                object_name=object_name,
                file_path=file_path
            )
        except S3Error as e:
            raise RuntimeError(f"Failed to upload {file_path} to {object_name}: {e}")
    
    def upload_file_data(self, file_data: bytes, object_name: str, content_type: str = "application/octet-stream"):
        """Upload file data directly from bytes"""
        try:
            file_stream = io.BytesIO(file_data)
            self.client.put_object(
                bucket_name=self.config.bucket_name,
                object_name=object_name,
                data=file_stream,
                length=len(file_data),
                content_type=content_type
            )
        except S3Error as e:
            raise RuntimeError(f"Failed to upload data to {object_name}: {e}")
    
    def download_file(self, object_name: str, file_path: str):
        """Download file from MinIO to local path"""
        try:
            self.client.fget_object(
                bucket_name=self.config.bucket_name,
                object_name=object_name,
                file_path=file_path
            )
        except S3Error as e:
            raise RuntimeError(f"Failed to download {object_name} to {file_path}: {e}")
    
    def download_file_data(self, object_name: str) -> bytes:
        """Download file data as bytes"""
        try:
            response = self.client.get_object(
                bucket_name=self.config.bucket_name,
                object_name=object_name
            )
            return response.read()
        except S3Error as e:
            raise RuntimeError(f"Failed to download data from {object_name}: {e}")
        finally:
            if 'response' in locals():
                response.close()
                response.release_conn()
    
    def get_presigned_url(self, object_name: str, expires: timedelta = timedelta(hours=1)):
        """Get presigned URL for public access to an object"""
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.config.bucket_name,
                object_name=object_name,
                expires=expires
            )
            return url
        except S3Error as e:
            raise RuntimeError(f"Failed to generate presigned URL for {object_name}: {e}")
    
    def get_presigned_upload_url(self, object_name: str, expires: timedelta = timedelta(hours=1)):
        """Get presigned URL for uploading an object"""
        try:
            url = self.client.presigned_put_object(
                bucket_name=self.config.bucket_name,
                object_name=object_name,
                expires=expires
            )
            return url
        except S3Error as e:
            raise RuntimeError(f"Failed to generate presigned upload URL for {object_name}: {e}")
    
    def delete_file(self, object_name: str):
        """Delete an object from MinIO"""
        try:
            self.client.remove_object(
                bucket_name=self.config.bucket_name,
                object_name=object_name
            )
        except S3Error as e:
            raise RuntimeError(f"Failed to delete {object_name}: {e}")
    
    def list_objects(self, prefix: str = None, recursive: bool = True):
        """List objects in the bucket"""
        try:
            objects = self.client.list_objects(
                bucket_name=self.config.bucket_name,
                prefix=prefix,
                recursive=recursive
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            raise RuntimeError(f"Failed to list objects: {e}")
    
    def object_exists(self, object_name: str) -> bool:
        """Check if an object exists in the bucket"""
        try:
            self.client.stat_object(
                bucket_name=self.config.bucket_name,
                object_name=object_name
            )
            return True
        except S3Error:
            return False
    
    def get_object_stat(self, object_name: str):
        """Get object statistics (size, etag, etc.)"""
        try:
            stat = self.client.stat_object(
                bucket_name=self.config.bucket_name,
                object_name=object_name
            )
            return {
                'size': stat.size,
                'etag': stat.etag,
                'last_modified': stat.last_modified,
                'content_type': stat.content_type
            }
        except S3Error as e:
            raise RuntimeError(f"Failed to get stats for {object_name}: {e}")
    
    async def upload_file_content(self, file_path: str, content: bytes, content_type: str = 'application/octet-stream') -> bool:
        """Upload file content directly from bytes"""
        try:
            from io import BytesIO
            
            # Convert bytes to BytesIO stream
            content_stream = BytesIO(content)
            content_length = len(content)
            
            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.config.bucket_name,
                object_name=file_path,
                data=content_stream,
                length=content_length,
                content_type=content_type
            )
            
            return True
        except S3Error as e:
            print(f"Failed to upload content to {file_path}: {e}")
            return False
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists in MinIO"""
        try:
            self.client.stat_object(
                bucket_name=self.config.bucket_name,
                object_name=file_path
            )
            return True
        except S3Error:
            return False
    
    def create_bucket_if_not_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(self.config.bucket_name):
                self.client.make_bucket(self.config.bucket_name)
        except S3Error as e:
            raise RuntimeError(f"Failed to create bucket {self.config.bucket_name}: {e}")
minio_instance = None
def get_minio_manager(config: MinioConfig = None):
    global minio_instance
    if minio_instance is None:
        if config is None:
            from config.config import settings
            config = MinioConfig(
                endpoint=settings.MINIO_BUCKET_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                bucket_name=settings.MINIO_BUCKET_NAME,
                port=settings.MINIO_BUCKET_PORT
            )
        minio_instance = MinioManager(config)
    return minio_instance