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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out-dir', help='Output directory', default='build')
    parser.add_argument('--force', help='Overwrite existing output',
                        action='store_true')
    parser.add_argument('src')
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
    return md5.hexdigest()


def json_files(src):
    files = []
    for f in os.listdir(src):
        name, ext = os.path.splitext(f)
        if ext == '.json':
            files.append(name)
    return files


def write_changes(src, out_dir, files):
    md5s = []
    with open(os.path.join(out_dir, '_changes'), 'w') as changes:
        changes.write('{"results":[\n')
        for i, f in enumerate(files):
            if i:
                changes.write(',\n')
            md5 = md5sum(os.path.join(src, f + '.json'))
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

        with open(path + '.json') as f:
            doc = json.load(f)
            doc['_id'] = key
            doc['_rev'] = '1-{}'.format(md5)
            doc['_revisions'] = {'start': 1, 'ids': [md5]}
            doc['_attachments'] = process_attachments(path)

            with open(os.path.join(out_dir, key), 'w') as out:
                json.dump(doc, out, separators=(',', ':'))
                out.write('\n')


def main():
    args = parse_args()

    files = json_files(args['src'])
    md5s = write_changes(args['src'], args['out_dir'], files)
    write_files(args['src'], args['out_dir'], files, md5s)

    out_dir = args['out_dir']
    with open(os.path.join(out_dir, 'index.html'), 'w') as f:
        f.write(json.dumps({"update_seq": len(files)}))
        f.write('\n')


if __name__ == '__main__':
    sys.exit(main())
