# services/sheets.py
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from django.conf import settings

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def company_drivers_weekly(spreadsheet_id, sheet_range):
    """
    Čita podatke iz Google Sheet-a koristeći Service Account.
    Vraća listu listi: [[header1, header2,...], [row1col1, row1col2,...], ...]
    """
    creds = Credentials.from_service_account_file(
        settings.SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )

    service = build("sheets", "v4", credentials=creds)

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=sheet_range
    ).execute()

    return result.get("values", [])
