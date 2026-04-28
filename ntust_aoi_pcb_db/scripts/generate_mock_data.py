import argparse
import datetime
import os
import random
import uuid
import sys
import time
import cv2
import numpy as np
from dotenv import load_dotenv
from pg_adapter import PostgresAdapter

# --- Configuration & Setup ---
load_dotenv()
DB_USER = os.getenv("DB_ROOT_USER")
DB_PASS = os.getenv("DB_ROOT_PASSWORD")

if not DB_USER or not DB_PASS:
    raise EnvironmentError("❌ Error: DB_ROOT_USER or DB_ROOT_PASSWORD not found in environment variables.")

# Postgres Connection String
POSTGRES_URI = f"postgresql://{DB_USER}:{DB_PASS}@localhost:5432/pcb_aoi_db"

# Camera Specs
RES_WIDTH = 3088
RES_HEIGHT = 2076
TARGET_SIZE_MB = 3.2

# Mapping
SIDE_MAP = {"TOP": "T", "BOTTOM": "B"}

def generate_base_image(base_storage_path):
    """
    Tries to load 'sample.png' or 'sample.jpg' from base_storage_path.
    If not found, generates a base noise image in memory.
    Returns: numpy array of the image.
    """
    # Check for sample images
    possible_samples = ["sample.png", "sample.jpg", "sample.jpeg"]
    sample_path = None
    
    for fname in possible_samples:
        path = os.path.join(base_storage_path, fname)
        if os.path.exists(path):
            sample_path = path
            break
            
    if sample_path:
        print(f"📄 Found sample image: {os.path.relpath(sample_path)}")
        img = cv2.imread(sample_path)
        if img is not None:
            # Resize to match camera specs
            if img.shape[1] != RES_WIDTH or img.shape[0] != RES_HEIGHT:
                print(f"   Resizing from {img.shape[1]}x{img.shape[0]} to {RES_WIDTH}x{RES_HEIGHT}...")
                img = cv2.resize(img, (RES_WIDTH, RES_HEIGHT))
            return img
        else:
            print("⚠️  Failed to load sample image. Falling back to noise generation.")

    print(f"🎲 Sample not found. Creating random noise image ({RES_WIDTH}x{RES_HEIGHT})...")
    # Generate random noise (grayscale)
    img_data = np.random.randint(0, 256, (RES_HEIGHT, RES_WIDTH), dtype=np.uint8)
    return img_data

def save_image(img_data, filepath, folder_path, quality=85):
    """
    Saves the image to disk with specific JPEG quality to approximate file size.
    Adjust quality to target ~3.2MB.
    """
    # Create folder if not exists
    os.makedirs(folder_path, exist_ok=True)
    
    # Text overlay to make image unique/debuggable
    display_text = os.path.basename(filepath)
    img_copy = img_data.copy()
    
    cv2.putText(img_copy, display_text, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255), 4)
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")
    cv2.putText(img_copy, timestamp, (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (255), 4)

    # Save
    cv2.imwrite(filepath, img_copy, [cv2.IMWRITE_JPEG_QUALITY, quality])

def main():
    parser = argparse.ArgumentParser(description="Generate mock PCB runs and images for performance testing.")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs to generate")
    parser.add_argument("--images_per_run", type=int, default=5, help="Number of images per run")
    parser.add_argument("--quality", type=int, default=85, help="JPEG Quality (0-100) to control file size")
    args = parser.parse_args()

    # DB Connection
    try:
        pg_adapter = PostgresAdapter(POSTGRES_URI)
        pg_adapter.connect()
    except Exception as e:
        print(f"❌ DB Connection Error: {e}")
        sys.exit(1)

    # Prepare Storage
    base_storage_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "images"))
    date_str = datetime.datetime.now().strftime("%Y%m%d")

    # Generate one base image to reuse (faster than generating random noise every time)
    base_img = generate_base_image(base_storage_path)
    
    total_images = args.runs * args.images_per_run
    print(f"🚀 Starting generation: {args.runs} Runs x {args.images_per_run} Images = {total_images} Total Images")
    print(f"📸 Resolution: {RES_WIDTH}x{RES_HEIGHT}")
    print(f"💾 Target path: {os.path.relpath(base_storage_path)}")

    start_time = time.time()
    
    for r in range(args.runs):
        run_code = f"RUN_{random.randint(100000, 999999)}_{r}"
        
        # Run Metadata
        board_code = "M18"
        run_condition = random.choice(["P", "F"])
        side = "TOP"
        illumination = "LR"
        
        # New Folder Structure: images/{board}/{date}/{side}/{illumination}/{run}
        # Note: date_str is already YYYYMMDD
        rel_run_path = os.path.join(board_code, date_str, side, illumination, run_code)
        run_dir = os.path.join(base_storage_path, rel_run_path)
        
        images_meta = []
        
        for i in range(args.images_per_run):
            row = i // 2
            col = i % 2
            filename = f"{board_code}-{run_condition}-{SIDE_MAP[side]}-{illumination}-{row}-{col}.jpg"
            filesize = 0
            
            # Save File
            abs_filepath = os.path.join(run_dir, filename)
            save_image(base_img, abs_filepath, run_dir, quality=args.quality)
            
            try:
                filesize = os.path.getsize(abs_filepath)
            except OSError:
                pass

            # Relative path for DB storage (URL friendly)
            # board/date/side/illumination/run/filename
            db_file_path = f"{board_code}/{date_str}/{side}/{illumination}/{run_code}/{filename}"

            # Metadata
            images_meta.append({
                "image_id": str(uuid.uuid4()),
                "path": db_file_path, # Storing relative path
                "row": row,
                "col": col,
                "condition": "FAIL" if run_condition == "F" else "PASS",
                "capture_time": datetime.datetime.now(),
                "file_info": {
                    "name": filename,
                    "checksum": "mock_md5_placeholder", 
                    "size_bytes": filesize
                }
            })
            
            # Simple progress log
            if (i + 1) % 10 == 0:
                print(f"   Run {r+1}: Generated {i+1}/{args.images_per_run} images...")

        # Insert Run to Postgres
        run_doc = {
            "run_code": run_code,
            "machine_id": "MOCK_GEN_01",
            "board_code": board_code,
            "date_str": date_str,
            "side": side,
            "illumination": illumination,
            "start_time": datetime.datetime.now(),
            "status": "COMPLETED",
            "note": f"Performance Test Data. {args.images_per_run} images.",
            "images": images_meta,
            "created_at": datetime.datetime.now()
        }
        
        pg_adapter.insert_run(run_doc)
        print(f"✅ Run {run_code} inserted with {len(images_meta)} images.")

    pg_adapter.close()
    elapsed = time.time() - start_time
    print(f"🎉 Done! Generated {total_images} images in {elapsed:.2f} seconds.")
    print(f"   Avg speed: {total_images/elapsed:.2f} images/sec")

if __name__ == "__main__":
    main()
