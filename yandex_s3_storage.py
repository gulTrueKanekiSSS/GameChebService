from storages.backends.s3boto3 import S3Boto3Storage

class ClientDocsStorage(S3Boto3Storage):
    bucket_name = "gamecheb"
    file_overwrite = False