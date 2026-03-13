from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
import os
import json
from urllib.parse import urlencode
from google_auth_oauthlib.flow import Flow

app = FastAPI()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")  # we'll set this after deploy
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# In-memory "database" for demo (one user)
TOKENS_STORE = {}
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

@app.get("/auth/google/drive")
def auth_google_drive():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI]
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = GOOGLE_REDIRECT_URI

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    # store state if you want to validate, skipped for demo
    return RedirectResponse(auth_url)

@app.get("/oauth2/callback/google")
async def oauth2_callback_google(request: Request):
    code = request.query_params.get("code")
    if not code:
        return JSONResponse({"error": "missing code"}, status_code=400)

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI]
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = GOOGLE_REDIRECT_URI

    flow.fetch_token(code=code)
    credentials = flow.credentials

    TOKENS_STORE["demo-user-1"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }

    return JSONResponse({"status": "connected", "user_id": "demo-user-1"})

@app.post("/get-template-from-drive")
async def get_template_from_drive(request: Request):
    body = await request.json()
    document_type = body.get("document_type")
    jurisdiction = body.get("jurisdiction")
    category = body.get("category")

    # TODO: use Drive API + tokens in TOKENS_STORE to find and download the right file
    # For now, return a dummy template_text so Airia integration works
    template_text = f"Dummy template for {document_type} / {jurisdiction} with placeholders like [[COMPANY_NAME]]."

    return {
        "template_file_name": f"{document_type}-{jurisdiction}-Base.txt",
        "template_text": template_text,
        "category": category,
    }
