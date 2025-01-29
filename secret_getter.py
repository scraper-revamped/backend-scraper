# from google.cloud import secretmanager
# import json
# from google.oauth2 import service_account  # Correct import for service account credentials
# from google.cloud import storage

# def get_service_account_credentials():
#     # Create the Secret Manager client
#     client = secretmanager.SecretManagerServiceClient()

#     # Replace <PROJECT-ID> with your Google Cloud Project ID
#     secret_name = "projects/scraper2-443707/secrets/rev_sec2/versions/latest"

#     # Access the secret
#     response = client.access_secret_version(name=secret_name)

#     # Decode the secret payload
#     secret_payload = response.payload.data.decode("UTF-8")
#     print("Service account key loaded successfully.")

#     # Load the credentials
#     credentials_dict = json.loads(secret_payload)
#     credentials = service_account.Credentials.from_service_account_info(credentials_dict)
#     return credentials


from google.cloud import secretmanager
import json
from google.oauth2 import service_account
from google.auth import default
import os 
import logging
from dotenv import load_dotenv
load_dotenv()
logging.basicConfig(level=logging.INFO)
def get_service_account_credentials():
    try:
        # Retrieve the secret from the environment variable
        secret_payload = os.getenv("SERVICE_ACCOUNT_JSON")
        if not secret_payload:
            raise ValueError("Service account JSON not found in environment variable.")

        # Load the credentials
        credentials_dict = json.loads(secret_payload)
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)
        return credentials
    except Exception as e:
        logging.error(f"Error retrieving or parsing the secret: {e}")
        raise


# def get_service_account_credentials():
#     # Create the Secret Manager client
#     client = secretmanager.SecretManagerServiceClient()

#     # Secret name and version (update with your project and secret details)
#     secret_name = "projects/scraper2-443707/secrets/rev_sec2/versions/latest"

#     try:
#         # Access the secret
#         response = client.access_secret_version(name=secret_name)

#         # Decode the secret payload
#         secret_payload = response.payload.data.decode("UTF-8")
#         print("Service account key loaded successfully.")

#         # Load the credentials
#         credentials_dict = json.loads(secret_payload)
#         credentials = service_account.Credentials.from_service_account_info(credentials_dict)
#         return credentials
#     except Exception as e:
#         print(f"Error retrieving or parsing the secret: {e}")
#         raise
