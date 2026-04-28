import psycopg2
from psycopg2.extras import execute_values
import os
import uuid
import datetime
import json

class PostgresAdapter:
    def __init__(self, connection_string):
        self.conn_str = connection_string
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(self.conn_str)
            self.conn.autocommit = False # Handle transactions manually for batching
            print("✅ Connected to PostgreSQL")
        except Exception as e:
            print(f"❌ Postgres Connection Error: {e}")
            raise e

    def close(self):
        if self.conn:
            self.conn.close()

    def insert_run(self, run_data):
        """
        Inserts a run and its images into Postgres.
        run_data: dict matching the structure used in generate_mock_data.py
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        try:
            # 1. Insert Run
            run_query = """
                INSERT INTO runs (
                    run_code, machine_id, board_code, date_str, 
                    side, illumination, status, note, start_time, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(run_query, (
                run_data["run_code"],
                run_data["machine_id"],
                run_data["board_code"],
                run_data["date_str"],
                run_data["side"],
                run_data["illumination"],
                run_data["status"],
                run_data.get("note", ""),
                run_data["start_time"],
                run_data["created_at"]
            ))

            # 2. Insert Images (Batch)
            if run_data.get("images"):
                image_query = """
                    INSERT INTO images (
                        image_id, run_code, file_path, row_idx, col_idx, 
                        condition, capture_time, file_name, file_size_bytes, checksum
                    ) VALUES %s
                """
                
                # Prepare data tuples
                images_tuples = []
                for img in run_data["images"]:
                     images_tuples.append((
                        img["image_id"],
                        run_data["run_code"], # FK
                        img["path"],
                        img["row"],
                        img["col"],
                        img["condition"],
                        img["capture_time"],
                        img["file_info"]["name"],
                        img["file_info"]["size_bytes"],
                        img["file_info"].get("checksum", "")
                    ))

                execute_values(cursor, image_query, images_tuples)

            self.conn.commit()
            return True

        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error inserting run {run_data.get('run_code')}: {e}")
            raise e
        finally:
            cursor.close()

    def get_filenames_by_date(self, date_str):
        """
        Retrieves all file paths for a specific date.
        """
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor()
        query = """
            SELECT i.file_path 
            FROM images i
            JOIN runs r ON i.run_code = r.run_code
            WHERE r.date_str = %s
        """
        cursor.execute(query, (date_str,))
        rows = cursor.fetchall()
        cursor.close()
        return [r[0] for r in rows]

    def add_field_camera_temp(self):
        """
        Schema Evolution Test: Adds 'camera_temperature' column to images table.
        """
        if not self.conn:
            self.connect()
            
        cursor = self.conn.cursor()
        try:
            # Check if column exists first to avoid error? Or just let it fail if exists.
            query = "ALTER TABLE images ADD COLUMN IF NOT EXISTS camera_temperature FLOAT;"
            cursor.execute(query)
            self.conn.commit()
            print("✅ Schema Altered: Added 'camera_temperature' to 'images' table.")
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Schema Evolution Error: {e}")
            raise e
        finally:
            cursor.close()

    def bulk_update(self, count, pattern="BENCH_%"):
        """
        Update 'status' of 'count' oldest runs matching the pattern to 'VERIFIED'.
        """
        if not self.conn:
            self.connect()
        cursor = self.conn.cursor()
        try:
            # Subquery to select IDs
            query = """
                UPDATE runs
                SET status = 'VERIFIED'
                WHERE run_code IN (
                    SELECT run_code FROM runs 
                    WHERE run_code LIKE %s
                    ORDER BY created_at ASC LIMIT %s
                )
            """
            cursor.execute(query, (pattern, count))
            self.conn.commit()
            return cursor.rowcount
        except Exception as e:
            print(f"❌ Postgres Bulk Update Error: {e}")
            self.conn.rollback()
            raise e
        finally:
            cursor.close()

    def bulk_delete(self, count, pattern="BENCH_%"):
        """
        Delete 'count' oldest runs matching the pattern.
        """
        if not self.conn:
            self.connect()
        cursor = self.conn.cursor()
        try:
            query = """
                DELETE FROM runs
                WHERE run_code IN (
                    SELECT run_code FROM runs 
                    WHERE run_code LIKE %s
                    ORDER BY created_at ASC LIMIT %s
                )
            """
            cursor.execute(query, (pattern, count))
            self.conn.commit()
            return cursor.rowcount
        except Exception as e:
            print(f"❌ Postgres Bulk Delete Error: {e}")
            self.conn.rollback()
            raise e
        finally:
            cursor.close()

    def cleanup_benchmarks(self, pattern="BENCH_%"):
        """
        Delete ALL runs matching the benchmark pattern.
        """
        if not self.conn:
            self.connect()
        cursor = self.conn.cursor()
        try:
            query = "DELETE FROM runs WHERE run_code LIKE %s"
            cursor.execute(query, (pattern,))
            deleted_count = cursor.rowcount
            self.conn.commit()
            print(f"🧹 Cleaned up {deleted_count} benchmark runs.")
            return deleted_count
        except Exception as e:
            print(f"❌ Cleanup Error: {e}")
            self.conn.rollback()
            raise e
        finally:
            cursor.close()
