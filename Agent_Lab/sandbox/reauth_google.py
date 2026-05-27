import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
client_secret_path = os.path.join(PROJECT_ROOT, 'credentials', 'client_secret.json')
token_path = os.path.join(PROJECT_ROOT, 'credentials', 'token_sheets.json')

print(f"Project root: {PROJECT_ROOT}")
print(f"Reading client secret from: {client_secret_path}")
print(f"Will save token to: {token_path}")

flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
creds = flow.run_local_server(port=0)

with open(token_path, 'w') as token:
    token.write(creds.to_json())

print("Successfully authenticated and saved token!")
