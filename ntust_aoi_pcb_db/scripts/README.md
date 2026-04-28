# Scripts Guide

This folder contains utility scripts for the AOI system.

## Prerequisites
Ensure Python dependencies are installed:
```bash
pip install -r ../requirements.txt
```
Ensure your `.env` file is configured with `DB_ROOT_USER` and `DB_ROOT_PASSWORD`.

## Available Scripts

### 1. Mock Data Generator (`generate_mock_data.py`)
Generates synthetic AOI runs and images, inserting metadata directly into PostgreSQL and saving images to the disk.

**Usage:**
```bash
python scripts/generate_mock_data.py --runs 10 --images_per_run 5
```
*   `--runs`: Number of inspection runs to simulate.
*   `--images_per_run`: Number of images per run.
*   `--quality`: JPEG quality (0-100) to control file size.

### 2. Database Reset (`reset_db.py`)
**WARNING**: This script permanently deletes ALL data from the `runs` and `images` tables. Use with caution.

**Usage:**
```bash
python scripts/reset_db.py
```
*   Prompts for confirmation (y/n) before deletion.

### 3. Image Import (`import_images.py`)
Scans the locally mounted `images/` directory and syncs missing runs and images into the database. Use this if you have image files but lost the database records.

**Usage:**
```bash
python scripts/import_images.py
```
*   Expects directory structure: `images/{board}/{date}/{side}/{illumination}/{run}/{filename}`.

### 4. Folder Monitor (`folder_monitor.py`)
Runs as a background process to watch a specific directory for new images. When a third-party camera software saves an image (like `.jpg` or `.png`) into this folder, it automatically inserts the image path and mocked metadata into the PostgreSQL database.

**Usage:**
```bash
# Set IMAGE_WATCH_DIR in .env or run directly
python scripts/folder_monitor.py
```
*   Configurable target directory via `IMAGE_WATCH_DIR` in `.env`.
*   Uses `watchdog` to efficiently listen for filesystem events.
