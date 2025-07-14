"""
Google OAuth authentication handling module.
"""
import os
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_flow():
    """Creates and returns a Google OAuth2 flow object."""
    return Flow.from_client_secrets_file(
        os.getenv("GOOGLE_CLIENT_SECRET_FILE"),
        scopes=[os.getenv("GOOGLE_SCOPES")],
        redirect_uri='http://localhost:5000/callback'
    )

def get_authorization_url():
    """Gets the Google OAuth2 authorization URL."""
    flow = create_flow()
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url

def exchange_code_for_credentials(authorization_response):
    """Exchanges authorization code for credentials."""
    flow = create_flow()
    flow.fetch_token(authorization_response=authorization_response)
    return flow.credentials

def credentials_to_dict(creds):
    """Converts credentials object to dictionary for session storage."""
    return {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }
