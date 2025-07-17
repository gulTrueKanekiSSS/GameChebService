import os
from storages.backends.s3boto3 import S3Boto3Storage

class ClientDocsStorage(S3Boto3Storage):
    bucket_name = os.getenv("AWS_STORAGE_BUCKET_NAME", "gamecheb")
    endpoint_url = os.getenv("AWS_S3_ENDPOINT_URL", "https://storage.yandexcloud.net")
    file_overwrite = False
    default_acl = None
