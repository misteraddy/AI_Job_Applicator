from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]

flow = InstalledAppFlow.from_client_secrets_file(
    "credentials.json",
    SCOPES
)

credentials = flow.run_local_server(
    port=0,
    access_type="offline",
    prompt="consent"
)

print("\nACCESS TOKEN:")
print(credentials.token)

print("\nREFRESH TOKEN:")
print(credentials.refresh_token)

print("\nCLIENT ID:")
print(credentials.client_id)

print("\nCLIENT SECRET:")
print(credentials.client_secret)