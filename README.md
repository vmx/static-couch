static-couch
============

static-couch is a script that creates a static set of files that can be
replicated into a Couch. Currently only PouchDB is supported.

It takes a directory full of JSON files and binary attachments as an input
and will create a directory that can then be put onto a simple web server.

static-couch is used in cases where you want to support a one time
uni-directional replication without the need of a full blown Apache CouchDB
installation.


Directory structure
-------------------

The input directory for the script expects the files in the following
structure:

    +-- doc1.json
    +-- doc2.json
    +-- doc2/
    |   +-- attachment.png
    |   +-- anotherone.txt
    |   \-- somesubdir/
    |       +-- even.jpg
    |       \-- more.txt
    +-- doc3.json
    \-- doc3/
        \-- singleattachment.png

The output directory will contain a file calles `index.html`. In reality it's
a JSON files, but most web servers are already configured to serve up the
contents of an `index.html` when you access the direcoty.


Static version of an Apache CouchDB instance
--------------------------------------------

If you want to create a replicatable static version of an Apache CouchDB
instance, you supply an URL as source.


Dependencies
------------

 - requests


License
-------

static-couch is licensed under the MIT License.
