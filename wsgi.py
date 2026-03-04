#!/usr/bin/python3
'''
uwsgi backend for smokesignal

The browser provides the camera (scanning) and screen (QR display).
This backend manages the protocol state and file I/O.

endpoints:
    GET  /              - serve index.html
    POST /scan          - browser sends decoded QR data to backend
    GET  /qrdata        - backend sends next QR code data to browser
    POST /send          - initiate sending a file
    POST /upload        - upload a file to send
    GET  <file>         - serve JS/CSS files

for iSH/iPhone: run with
    uwsgi --http :8080 --wsgi-file wsgi.py --callable application
or for testing:
    python3 wsgi.py
'''
import os, json, logging, base64, threading  # pylint: disable=multiple-imports
import posixpath as wwwpath
from datetime import datetime
from hashlib import sha256

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)
logging.warning('wsgi script starting')

STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
RECEIVED_DIR = os.path.join(STATIC_DIR, 'received')
os.makedirs(RECEIVED_DIR, exist_ok=True)

HASH = sha256
HASHLENGTH = len(HASH(b'').digest())
EMPTY_HASH = bytes(HASHLENGTH)
CHUNKSIZE = 128
SERIAL_BITS = 32
SERIAL_BYTES = SERIAL_BITS // 8
LENGTH_BITS = 32
LENGTH_BYTES = LENGTH_BITS // 8
PACKET_LENGTH = SERIAL_BYTES + LENGTH_BYTES + CHUNKSIZE + HASHLENGTH
SERIAL_MODULUS = 1 << SERIAL_BITS

def chunkhash(data):
    '''return binary hash of data'''
    return HASH(data).digest()

class Puff():
    '''
    data for a single transceive QR code

    serial, SERIAL_BYTES bytes
    length, LENGTH_BYTES bytes
    chunk, CHUNKSIZE bytes
    hashed, HASHLENGTH bytes
    '''
    def __init__(self, data=b'', **kwargs):
        if data:
            offset = SERIAL_BYTES
            self.serial = int.from_bytes(data[:offset], 'big')
            length = int.from_bytes(data[offset:offset + LENGTH_BYTES], 'big')
            offset += LENGTH_BYTES
            self.chunk = data[offset:offset + length]
            offset += CHUNKSIZE
            self.hashed = data[offset:]
        else:
            self.serial = kwargs.get('serial', 0)
            self.chunk = kwargs.get('chunk', b'')
            self.hashed = kwargs.get('hashed', EMPTY_HASH)

    def pack(self):
        '''pack into bytes for QR code'''
        return (self.serial.to_bytes(SERIAL_BYTES, 'big') +
                len(self.chunk).to_bytes(LENGTH_BYTES, 'big') +
                self.chunk.ljust(CHUNKSIZE, b'\0') +
                self.hashed)

    def checkhash(self):
        '''hash of serial + length + chunk'''
        data = (
            self.serial.to_bytes(SERIAL_BYTES, 'big') +
            len(self.chunk).to_bytes(LENGTH_BYTES, 'big') +
            self.chunk
        )
        return chunkhash(data)

class TransceiverState():
    '''
    manages the send/receive protocol state

    the browser is our camera and screen:
    - it scans QR codes from the peer and POSTs binary data to /scan
    - it GETs /qrdata for the next QR code to display to the peer
    '''
    def __init__(self):
        self.lock = threading.Lock()
        self.send_file = None
        self.send_fh = None
        self.sent = Puff()
        self.recv_file = None
        self.recv_fh = None
        self.last_seen = b''
        self.qr_out = None  # bytes to display as QR

    def start_send(self, filepath):
        '''begin sending a file'''
        with self.lock:
            if self.send_fh:
                self.send_fh.close()
            self.send_file = filepath
            self.send_fh = open(filepath, 'rb')
            self.sent = Puff()
            self._load_next_chunk()
            logging.info('started sending %s', filepath)

    def start_send_data(self, data, filename=None):
        '''begin sending raw data (from upload)'''
        filepath = os.path.join(STATIC_DIR, 'uploads',
                                filename or 'upload-' +
                                datetime.now().isoformat())
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as out:
            out.write(data)
        self.start_send(filepath)

    def _load_next_chunk(self):
        '''read next chunk and prepare QR data'''
        if self.send_fh:
            chunk = self.send_fh.read(CHUNKSIZE)
            if chunk:
                self.sent.chunk = chunk
                self.qr_out = self.sent.pack()
                logging.debug('loaded chunk %d, %d bytes',
                              self.sent.serial, len(chunk))
            else:
                logging.info('finished sending %s', self.send_file)
                self.send_fh.close()
                self.send_fh = None
                self.send_file = None
                self.sent = Puff()
                self.qr_out = None

    def handle_scan(self, data):
        '''
        process QR data scanned by the browser from the peer

        data is raw bytes (base64-decoded by the caller)
        '''
        with self.lock:
            if data == self.last_seen:
                return  # duplicate
            self.last_seen = data

            if len(data) >= PACKET_LENGTH:
                received = Puff(data=data)
                logging.debug('received puff: serial=%d, chunk=%d bytes',
                              received.serial, len(received.chunk))

                # check if peer acknowledged our last send
                if received.hashed == self.sent.checkhash():
                    logging.debug('peer acked our chunk %d',
                                  self.sent.serial)
                    self.sent.serial = (
                        (self.sent.serial + 1) % SERIAL_MODULUS
                    )
                    self._load_next_chunk()

                # save received data
                if received.chunk:
                    if not self.recv_fh:
                        self.recv_file = os.path.join(
                            RECEIVED_DIR,
                            datetime.now().isoformat()
                        )
                        self.recv_fh = open(self.recv_file, 'wb')
                    self.recv_fh.write(received.chunk)
                    self.recv_fh.flush()
                    logging.debug('saved %d bytes to %s',
                                  len(received.chunk), self.recv_file)
                    # acknowledge with hash
                    self.sent.hashed = received.checkhash()
                    self.qr_out = self.sent.pack()
                else:
                    # empty chunk = peer finished sending
                    if self.recv_fh:
                        self.recv_fh.close()
                        self.recv_fh = None
                        logging.info('finished receiving %s', self.recv_file)
                        self.recv_file = None

    def get_qrdata(self):
        '''return current QR data as base64, or None'''
        with self.lock:
            if self.qr_out:
                return base64.b64encode(self.qr_out).decode('ascii')
            return None

STATE = TransceiverState()

def application(environ, start_response):
    '''WSGI entry point'''
    method = environ.get('REQUEST_METHOD', 'GET')
    path = wwwpath.basename(environ.get('PATH_INFO', '/'))

    if path == '' and method == 'GET':
        return serve_file('index.html', start_response)
    elif os.path.exists(path) and method == 'GET':
        return serve_file(path, start_response)
    elif path == 'scan' and method == 'POST':
        return api_scan(environ, start_response)
    elif path == 'qrdata' and method == 'GET':
        return api_qrdata(start_response)
    elif path == 'send' and method == 'POST':
        return api_send(environ, start_response)
    elif path == 'upload' and method == 'POST':
        return api_upload(environ, start_response)
    else:
        return not_found(start_response)

def serve_file(filename, start_response):
    '''
    serve static file
    '''
    filepath = os.path.join(STATIC_DIR, filename)
    if not os.path.exists(filepath):
        logging.error('%r not found', filepath)
        return not_found(start_response)
    content_types = {
        '.html': 'text/html', '.js': 'application/javascript',
        '.css': 'text/css', '.png': 'image/png',
    }
    ext = os.path.splitext(filename)[1]
    ctype = content_types.get(ext, 'application/octet-stream')
    with open(filepath, 'rb') as infile:
        body = infile.read()
    start_response('200 OK', [
        ('Content-Type', ctype),
        ('Content-Length', str(len(body))),
    ])
    return [body]

def json_response(data, start_response, status='200 OK'):
    '''helper for JSON responses'''
    body = json.dumps(data).encode()
    start_response(status, [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(body))),
    ])
    return [body]

def read_body(environ):
    '''read request body'''
    length = int(environ.get('CONTENT_LENGTH', 0))
    return environ['wsgi.input'].read(length)

def api_scan(environ, start_response):
    '''browser sends decoded QR data'''
    try:
        payload = json.loads(read_body(environ))
        raw = base64.b64decode(payload['data'])
        STATE.handle_scan(raw)
        return json_response({'ok': True}, start_response)
    except (ValueError, KeyError) as err:
        logging.error('bad scan payload: %s', err)
        return json_response({'ok': False, 'error': str(err)},
                             start_response, '400 Bad Request')

def api_qrdata(start_response):
    '''return next QR data for browser to display'''
    data = STATE.get_qrdata()
    return json_response({'data': data}, start_response)

def api_send(environ, start_response):
    '''initiate sending a local file'''
    try:
        payload = json.loads(read_body(environ))
        filepath = payload['path']
        if not os.path.isfile(filepath):
            return json_response({'ok': False, 'error': 'file not found'},
                                 start_response, '404 Not Found')
        STATE.start_send(filepath)
        return json_response({'ok': True}, start_response)
    except (ValueError, KeyError) as err:
        return json_response({'ok': False, 'error': str(err)},
                             start_response, '400 Bad Request')

def api_upload(environ, start_response):
    '''upload a file to send to peer'''
    try:
        payload = json.loads(read_body(environ))
        data = base64.b64decode(payload['data'])
        filename = payload.get('filename', None)
        STATE.start_send_data(data, filename)
        return json_response({'ok': True}, start_response)
    except (ValueError, KeyError) as err:
        return json_response({'ok': False, 'error': str(err)},
                             start_response, '400 Bad Request')

def not_found(start_response):
    '''404'''
    body = b'404 Not Found'
    start_response('404 Not Found', [
        ('Content-Type', 'text/plain'),
        ('Content-Length', str(len(body))),
    ])
    return [body]

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    print('serving on http://127.0.0.1:8080')
    make_server('127.0.0.1', 8080, application).serve_forever()
