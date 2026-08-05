from google.cloud import storage
import pandas as pd 
import os
from secret_getter import get_service_account_credentials
import logging

logging.basicConfig(level=logging.INFO)

TENDERS_PREFIX = "الاتصالات_وتقنية_المعلومات/"


def delete_existing_files(bucket_name):
    """Delete the previous tenders spreadsheet(s) so only the latest remains.
    Scans only the tenders folder (prefix), not the whole bucket."""
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        deleted = 0
        for blob in bucket.list_blobs(prefix=TENDERS_PREFIX):
            if blob.name.startswith(TENDERS_PREFIX + "tenders_"):
                blob.delete()
                deleted += 1
        logging.info("Deleted %d previous tender file(s) under %s", deleted, TENDERS_PREFIX)
    except Exception as e:
        logging.error(f"Error deleting files: {e}")


def prune_debug_snapshots(bucket_name="scraping_revamped_4", prefix="debug/", retention_days=14):
    """Delete debug snapshot blobs older than retention_days so debug/ doesn't
    grow forever. Best-effort; never raises."""
    try:
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        deleted = 0
        for blob in bucket.list_blobs(prefix=prefix):
            if blob.time_created and blob.time_created < cutoff:
                blob.delete()
                deleted += 1
        if deleted:
            logging.info("Pruned %d debug snapshot(s) older than %d days", deleted, retention_days)
    except Exception as e:
        logging.error("Error pruning debug snapshots: %s", e)

def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    logging.info(f"Uploaded {source_file_name} to {destination_blob_name}")

def save_to_storage(df, term, username):
    logging.info(f"Saving data for term: {term}")
    try:
        today_date = pd.to_datetime('today').strftime('%Y-%m-%d-%h')
        file_name = f"tenders_{term}_{today_date}_{username}.xlsx"
        df.to_excel(file_name, index=False)
        logging.info(f"File saved locally: {file_name}")

        bucket_name = "scraping_revamped_4"
        logging.info(f"deleting file ....: {term}/{file_name}")
        delete_existing_files(bucket_name)
        logging.info(f"file deleted ....: {term}/{file_name}")
        upload_to_gcs(bucket_name, file_name, f"{term}/{file_name}")
        logging.info(f"File uploaded to GCS: {term}/{file_name}")

        os.remove(file_name)
    except Exception as e:
        logging.error(f"Error in save_to_storage: {str(e)}")
        raise
