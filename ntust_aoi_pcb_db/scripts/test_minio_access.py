import os
from minio import Minio
from dotenv import load_dotenv

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "192.168.40.21:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS_KEY", "aoi_admin")
MINIO_SECRET = os.getenv("MINIO_SECRET_KEY", "aoi@1234")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "aoi-images")

try:
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=False)
    
    print(f"Connecting to MinIO at {MINIO_ENDPOINT}...")
    buckets = client.list_buckets()
    print("Connection Successful! Available buckets:")
    for b in buckets:
        print(f" - {b.name}")
        
    print(f"\nChecking for objects in '{MINIO_BUCKET}'...")
    objects = client.list_objects(MINIO_BUCKET, recursive=True)
    for obj in objects:
        print(f"Found object: {obj.object_name} ({obj.size} bytes)")
        # Try to get a small piece of the first object
        data = client.get_object(MINIO_BUCKET, obj.object_name)
        chunk = data.read(1024)
        print(f"Successfully read start of {obj.object_name}")
        data.close()
        data.release_conn()
        break

except Exception as e:
    print(f"ERROR connecting to MinIO: {e}")
