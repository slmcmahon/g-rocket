from __future__ import print_function
import io

import os.path
import re
from datetime import datetime
from collections import namedtuple

from pymongo import MongoClient 

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive']

new_files_folder_id = '1f_4r0F3QFDvbdkyHxyPqLt3r--USuCQB'
processed_files_folder_id = '1ua-Hw-8AVC16TkOyenBIYSaTSKK7nLH1'

LogEntry = namedtuple("LogEntry", "date header content")


def get_files(service):
    try:
        query = "trashed = false and parents in '" + new_files_folder_id + "'"
        #query = ""
        files = service.files().list(
            q=query, fields="nextPageToken, files(id, name, mimeType)").execute()
        return files['files']
    except HttpError as error:
        print(F'An error occurred: {error}')
        return None


def get_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('drive', 'v3', credentials=creds)
    return service


def move_file(service, file_id):
    file = service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents'))
    file = service.files().update(fileId=file_id, addParents=processed_files_folder_id,
                                  removeParents=previous_parents, fields='id, parents').execute()
    return file.get('parents')


def download_file(service, file_id):
    request = service.files().export_media(fileId=file_id, mimeType='text/plain')
    file = io.BytesIO()
    downloader = MediaIoBaseDownload(file, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        #print(f'Download {int(status.progress() * 100)}.')

    return file.getvalue()

def write_to_db(records):
    client = MongoClient(os.getenv('PYMONGO_PERSONAL'))
    db = client['RocketNotes']
    col = db['notes']
    col.insert_many(records)


date_pattern = re.compile("\+.*?(\d{2}-\S{3}-\d{4})\s*[-]?\s*(.*)")


def main():
    try:
        service = get_service()

        records = []
        pdfs = {}

        for f in get_files(service):
            if f['mimeType'] == 'application/vnd.google-apps.document':
                data = download_file(service, f['id'])
                processed_text = data.decode('utf-8-sig')
                current = None
                for l in processed_text.splitlines():
                    if len(l) == 0:
                        continue

                    if l.startswith('+'):
                        dm = date_pattern.match(l)
                        date = dm[1] 
                        header = dm[2].strip()
                        
                        current = {}
                        current['date'] = date
                        current['header'] = header
                        current['content'] = ''
                        current['pdf'] = f"{f['name'].replace('Transcription ', '')}.pdf"
                        records.append(current)
                    else:
                        if current:
                            current['content'] += f'{l} '
            else:
                pdfs[f['name']] = f['id']
                                
                
            #move_file(service=service, file_id=f['id'])
        for r in records:
            r['content'] = r['content'].strip()
            r['pdf_file_id'] = pdfs[r['pdf']]
            print(f"{r['date']} ({r['header']})\n{r['content']}\n")
            
        if len(records) > 0:
            write_to_db(records)

    except HttpError as error:
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()
