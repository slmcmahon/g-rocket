import os.path
from pymongo import MongoClient
from grocket import GRocket

FOLDER_ID = '1f_4r0F3QFDvbdkyHxyPqLt3r--USuCQB'
BACKUP_FOLDER_ID = '1ua-Hw-8AVC16TkOyenBIYSaTSKK7nLH1'

gclient = GRocket(FOLDER_ID, BACKUP_FOLDER_ID)


def write_to_db(records):
    """ Writes records to the mongodb database database """
    client = MongoClient(os.getenv('PYMONGO_PERSONAL'))
    client['RocketNotes']['notes'].insert_many(records)


def main():
    """ Entry Point """
    try:
        records = []
        pdfs = {}

        for file in gclient.get_files():
            if file['mimeType'] == 'application/vnd.google-apps.document':
                txt = gclient.download_text(file['id'])
                pdf_name = f"{file['name'].replace('Transcription ', '')}.pdf"
                records.append(
                    {'txt': txt, 'id': file['id'], 'pdf_name': pdf_name})
            else:
                pdfs[file['name']] = file['id']

        for record in records:
            record['pdf_file_id'] = pdfs[record['pdf_name']]
            print(record['pdf_file_id'])

        if len(records) > 0:
            write_to_db(records)

        for record in records:
            gclient.backup_file(file_id=record['id'])
            gclient.backup_file(file_id=record['pdf_file_id'])

    except Exception as error:
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()
