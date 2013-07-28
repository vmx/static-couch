#!/usr/bin/env python3

import argparse
import base64
import hashlib
import io
import json
import mimetypes
import os
import shutil
import sys
import urllib

import requests


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--out-dir', help='Output directory', default='build')
    parser.add_argument('--force', help='Overwrite existing output',
                        action='store_true')
    parser.add_argument('src',
                        help='Input directory or URL to an Apache CouchDB')
    args = parser.parse_args()

    try:
        os.makedirs(args.out_dir, exist_ok=args.force)
    except OSError as ex:
        if ex.errno == 17:
            print("Directory '{}' already exists. To overwrite it, use the "
                  "--force option".format(args.out_dir))
        else:
            raise ex

    return {'src': args.src, 'out_dir': args.out_dir}


# Based on http://stackoverflow.com/questions/1131220/get-md5-hash-of-big-files-in-python
# (2013-07-07)
def md5sum(filename):
    md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        while True:
            data = f.read(md5.block_size*128)
            if not data:
                break
            md5.update(data)
    return md5


def create_digest(path, name):
    try:
        #md5 = md5sum(filename)
        md5 = md5sum(os.path.join(path, name + '.json'))
    except IOError as ex:
        md5 = hashlib.md5(b'{}')
    # Make sure the hash is different, even if the file contents is the same
    md5.update(name.encode('utf-8'))
    return md5.hexdigest()


def json_files(src):
    files = set()
    for f in os.listdir(src):
        name, ext = os.path.splitext(f)
        fullpath = os.path.join(src, f)
        # Store the names of all JSON files, but also all direcctories
        # without a corresponding JSON file
        if ext == '.json' or (ext == '' and os.path.isdir(fullpath)):
            files.add(name)
    return files


def write_changes(src, out_dir, files):
    md5s = []
    with open(os.path.join(out_dir, '_changes'), 'w') as changes:
        changes.write('{"results":[\n')
        for i, f in enumerate(files):
            if i:
                changes.write(',\n')
            md5 = create_digest(src, f)
            changes.write('{{"seq":{},"id":"{}","changes":[{{"rev":"1-{}"}}]}}'
                          .format(i+1, f, md5))
            md5s.append(md5)
        changes.write('\n],\n')
        changes.write('"last_seq":{}}}\n'.format(i+1))
    return md5s


def process_attachments(path):
    attachments = {}
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            att_path = os.path.join(dirpath, filename)
            contenttype = mimetypes.guess_type(att_path)[0]
            rel_path = os.path.relpath(att_path, path)
            with open(att_path, 'rb') as att:
                data = base64.b64encode(att.read())
            attachments[rel_path] = {
                'revops': 1,
                'content_type': contenttype,
                'data': data.decode('ascii')
            }
    return attachments


def write_files(src, out_dir, files, md5s):
    for key, md5 in zip(files, md5s):
        path = os.path.join(src, key)

        try:
            with open(path + '.json') as f:
                doc = json.load(f)
        # There's only a directory with attachments and not corresponding
        # JSON file
        except IOError as ex:
            doc = {}

        doc['_id'] = key
        doc['_rev'] = '1-{}'.format(md5)
        doc['_revisions'] = {'start': 1, 'ids': [md5]}
        doc['_attachments'] = process_attachments(path)

        with open(os.path.join(out_dir, key), 'w') as out:
            json.dump(doc, out, separators=(',', ':'))
            out.write('\n')


def from_dir(args):
    files = json_files(args['src'])
    md5s = write_changes(args['src'], args['out_dir'], files)
    write_files(args['src'], args['out_dir'], files, md5s)

    out_dir = args['out_dir']
    with open(os.path.join(out_dir, 'index.html'), 'w') as f:
        f.write(json.dumps({"update_seq": len(files)}))
        f.write('\n')


def from_couch(args):
    r = requests.get(args['src'])
    with open(os.path.join(args['out_dir'], 'index.html'), 'wb') as index:
        index.write(r.content)

    r = requests.get(args['src'] + '_changes')
    with open(os.path.join(args['out_dir'], '_changes'), 'wb') as changes:
        changes.write(r.content)
        doc_ids = [doc['id'] for doc in r.json()['results']]
        #print(docs)

    for doc_id in doc_ids:
        r = requests.get(args['src'] + doc_id, params={'attachments': 'true'},
                         headers={'Accept': 'application/json'})
        doc_path = os.path.join(args['out_dir'], doc_id)
        try:
            doc = open(doc_path, 'wb')
        except IOError as ex:
            os.makedirs(os.path.dirname(doc_path))
            doc = open(doc_path, 'wb')
        doc.write(r.content)
        doc.close()


def main():
    args = parse_args()

    if urllib.parse.urlparse(args['src']).scheme.startswith('http'):
        if args['src'][-1] != '/':
            args['src'] += '/'
        from_couch(args)
    else:
        from_dir(args)


if __name__ == '__main__':
    sys.exit(main())
