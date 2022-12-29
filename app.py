from __future__ import print_function
from grocket import GRocket

import os.path
import re

from pymongo import MongoClient

folder_id = '1f_4r0F3QFDvbdkyHxyPqLt3r--USuCQB'
backup_folder_id = '1ua-Hw-8AVC16TkOyenBIYSaTSKK7nLH1'

dateline_pattern = re.compile("\+.*?(\d{2}-\S{3}-\d{4})\s*[-]?\s*(.*)")

gclient = GRocket(folder_id, backup_folder_id)

def write_to_db(records):
    client = MongoClient(os.getenv('PYMONGO_PERSONAL'))
    client['RocketNotes']['notes'].insert_many(records)


def main():
    try:
        records = []
        pdfs = {}

        for f in gclient.get_files():
            if f['mimeType'] == 'application/vnd.google-apps.document':
                records.append(gclient.parse_text_file(f))
            else:
                pdfs[f['name']] = f['id']

            #gclient.backup_file(file_id=f['id'])
        for r in records:
            r['content'] = r['content'].strip()
            r['pdf_file_id'] = pdfs[r['pdf']]
            print(f"{r['date']} ({r['header']})\n{r['content']}\n")

        if len(records) > 0:
            write_to_db(records)

    except Exception as error:
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()
