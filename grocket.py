from __future__ import print_function
import io
import os
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


class GRocket():

    SCOPES = ['https://www.googleapis.com/auth/drive']
    DATELINE_PATTERN = re.compile("\+.*?(\d{2}-\S{3}-\d{4})\s*[-]?\s*(.*)")

    def __init__(self, folder_id, backup_folder_id):
        self.working_folder_id = folder_id
        self.backup_folder_id = backup_folder_id
        self._init_drive()

    def _init_drive(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file(
                'token.json', self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        self.service = build('drive', 'v3', credentials=creds)

    def get_service(self):
        return self.service

    def get_files(self):
        try:
            query = "trashed = false and parents in '" + self.working_folder_id + "'"
            files = self.service.files().list(
                q=query, fields="nextPageToken, files(id, name, mimeType)").execute()
            return files['files']
        except HttpError as error:
            print(F'An error occurred: {error}')
            return None

    def backup_file(self, file_id):
        file = self.service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        file = self.service.files().update(fileId=file_id, addParents=self.backup_folder_id,
                                           removeParents=previous_parents, fields='id, parents').execute()
        return file.get('parents')

    def download_file(self, file_id):
        request = self.service.files().export_media(
            fileId=file_id, mimeType='text/plain')
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            #print(f'Download {int(status.progress() * 100)}.')

        return file.getvalue()

    def parse_text_file(self, file):
        data = self.download_file(file['id'])
        processed_text = data.decode('utf-8-sig')
        entries = []
        current = None
        for l in processed_text.splitlines():
            if len(l) == 0:
                continue

            if l.startswith('+'):
                dm = self.DATELINE_PATTERN.match(l)
                date = dm[1]
                header = dm[2].strip()

                current = {}
                current['date'] = date
                current['header'] = header
                current['content'] = ''
                current['pdf'] = f"{file['name'].replace('Transcription ', '')}.pdf"
                entries.append(current)
            else:
                if current:
                    current['content'] += f'{l} '

        return entries
