from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
import os
from google_auth_oauthlib.flow import Flow

app = FastAPI()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Demo-only in-memory storage
TOKENS_STORE = {}
PKCE_STATE_STORE = {}  # state -> code_verifier
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")


def build_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )


@app.get("/auth/google/drive")
def auth_google_drive():
    flow = build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        code_challenge_method="S256",  # enable PKCE
    )

    # Store PKCE info keyed by state (demo only)
    PKCE_STATE_STORE[state] = {
        "code_verifier": flow.code_verifier,
    }

    return RedirectResponse(auth_url)


@app.get("/oauth2/callback/google")
async def oauth2_callback_google(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code:
        return JSONResponse({"error": "missing code"}, status_code=400)
    if not state or state not in PKCE_STATE_STORE:
        return JSONResponse({"error": "missing or invalid state"}, status_code=400)

    stored = PKCE_STATE_STORE.pop(state)

    flow = build_flow()
    # Restore PKCE verifier before fetching token
    flow.code_verifier = stored["code_verifier"]

    flow.fetch_token(code=code)
    credentials = flow.credentials

    TOKENS_STORE["demo-user-1"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes) if credentials.scopes else [],
    }

    return JSONResponse({"status": "connected", "user_id": "demo-user-1"})


@app.post("/get-template-from-drive")
async def get_template_from_drive(request: Request):
    body = await request.json()
    document_type = body.get("document_type")
    jurisdiction = body.get("jurisdiction")
    category = body.get("category")

    # TODO: use Drive API + tokens in TOKENS_STORE + FOLDER_ID to fetch real file
    # For now: dummy template so Airia integration works
    template_text = (
        f"Dummy template for {document_type} / {jurisdiction} "
        f"with placeholders like [[COMPANY_NAME]] and [[EFFECTIVE_DATE]]."
    )

    return {
        "template_file_name": f"{document_type}-{jurisdiction}-Base.txt",
        "template_text": template_text,
        "category": category,
    }
