#!/usr/bin/python3
'''
uwsgi backend for smokesignal

The browser provides the camera (scanning) and screen (QR display).
This backend manages the protocol state and file I/O.

endpoints:
    GET  /              - serve index.html
    POST /save          - browser sends decoded QR data to backend
    GET  <file>         - serve JS/CSS files

for iSH/iPhone: run with
    uwsgi --http :8080 --wsgi-file wsgi.py --callable application
or for testing:
    python3 wsgi.py
'''
import os, json, logging  # pylint: disable=multiple-imports
import posixpath as wwwpath  # pylint: disable=multiple-imports
from threading import Thread
from select import select
from smokesignal import newpath, SERIAL_BYTES, LENGTH_BYTES, CHUNKSIZE

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)
logging.warning('wsgi script starting')

PORT = int(os.getenv('PORT', '8080'))
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
RECEIVED_DIR = os.path.join(STATIC_DIR, 'received')
STATE = {  # mutable for maintaining state
    'outfile': None,
}
os.makedirs(RECEIVED_DIR, exist_ok=True)

def application(environ, start_response):
    '''
    WSGI entry point
    '''
    method = environ.get('REQUEST_METHOD', 'GET')
    path = wwwpath.basename(environ.get('PATH_INFO', '/'))
    result = not_found
    if path == '' and method == 'GET':
        environ['PATH_INFO'] = 'index.html'
        result = serve_file
    elif os.path.exists(path) and method == 'GET':
        environ['PATH_INFO'] = path
        result = serve_file
    elif path == 'save' and method == 'POST':
        result = api_save
    return result(environ, start_response)

def json_response(data, start_response, status='200 OK'):
    '''
    helper for JSON responses
    '''
    body = json.dumps(data).encode()
    start_response(status, [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(body))),
    ])
    return [body]

def read_body(environ):
    '''
    read request body
    '''
    length = int(environ.get('CONTENT_LENGTH', 0))
    return environ['wsgi.input'].read(length)

def api_save(environ, start_response):
    '''
    browser sends us chunk of data to save
    '''
    offset = 0
    response = {'ok': False, 'error': None}
    status = '400 bad request'
    try:
        payload = read_body(environ)
        content_type = environ.get('CONTENT_TYPE', '')
        logging.debug('content-type: %s, raw save data: %r',
                      content_type, payload)
        serial = int.from_bytes(payload[offset:SERIAL_BYTES], 'big')
        response['serial'] = serial
        offset += SERIAL_BYTES
        length = int.from_bytes(payload[offset:offset + LENGTH_BYTES], 'big')
        response['length'] = length
        offset += LENGTH_BYTES
        chunk = payload[offset:offset + length]
        if serial == 0 and length:
            # pylint: disable=consider-using-with
            STATE['outfile'] = newpath()
        if length:
            if length <= CHUNKSIZE:
                with open(STATE['outfile'], 'ab') as outfile:
                    if outfile.tell() == serial * CHUNKSIZE:
                        outfile.write(chunk)
                        outfile.flush()
                        response['written'] = True
                    else:
                        logging.error(
                            'file position %d incompatible with serial #%d',
                            outfile.tell(), serial
                        )
            else:
                logging.error('bad chunk length %d', length)
        else:
            STATE['outfile'] = None
            response['complete'] = True
        status = '200 success'
        response['ok'] = True
    except (ValueError, KeyError) as error:
        logging.error('bad scan payload: %s', error)
        response['error'] = error
    return json_response(response, start_response, status)

def not_found(environ, start_response):  # pylint: disable=unused-argument
    '''
    404 Not Found
    '''
    body = b'404 Not Found'
    start_response('404 Not Found', [
        ('Content-Type', 'text/plain'),
        ('Content-Length', str(len(body))),
    ])
    return [body]

def serve_file(environ, start_response):
    '''
    serve static file
    '''
    filename = environ['PATH_INFO']
    filepath = os.path.join(STATIC_DIR, filename)
    if not os.path.exists(filepath):
        logging.error('%r not found', filepath)
        return not_found(environ, start_response)
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

def background():
    '''
    iPhone trick for running from iSH

    runs in separate thread to keep server active while browser in foreground
    '''
    try:
        with open('/dev/location', encoding='utf-8') as infile:
            logging.debug('keepalive thread launched in background')
            while select([infile], [], [infile]):
                location = infile.read()
                logging.debug('location: %r', location)
                if not location:
                    break
    except FileNotFoundError:
        logging.debug('no /dev/location file found')

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    Thread(target=background, daemon=True).start()
    logging.info('attempting serving on http://127.0.0.1:%d', PORT)
    try:
        make_server('127.0.0.1', PORT, application).serve_forever()
    except OSError as problem:
        logging.error('cannot serve smokesignal on port %d: %s', PORT, problem)
        raise
