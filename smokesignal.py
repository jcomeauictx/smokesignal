#!/usr/bin/python3
'''
communicate visually with another computer using QR codes

QR codes sent and received start with a hash of the chunk
last received; the remainder is the chunk being sent
'''
# pylint: disable=c-extension-no-member  # for cv2
import sys, os, logging, posixpath  # pylint: disable=multiple-imports
# Windows should be able to handle posixpath, and we need it for URLs
from datetime import datetime
from hashlib import sha256
from tkinter import Tk, Label
try:
    import cv2
except ImportError:
    pass  # not available on iSH
import zbar, zmq  # pylint: disable=multiple-imports
from PIL import Image
from PIL.ImageTk import PhotoImage as Photo
from monkeypatch import qrcode

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

HASH = sha256
HASHLENGTH = len(HASH(b'').digest())
EMPTY_HASH = bytes(HASHLENGTH)
CHUNKSIZE = 128
SERIAL_BITS = 32
SERIAL_BYTES = SERIAL_BITS // 8
# store actual size of packet, since it will be padded for QR code
# 32 bits is probably way overkill, but think big, tech will improve
LENGTH_BITS = 32
LENGTH_BYTES = LENGTH_BITS // 8
PACKET_LENGTH = (
    SERIAL_BYTES +
    LENGTH_BYTES +
    CHUNKSIZE +
    HASHLENGTH
)
SERIAL_MODULUS = 1 << SERIAL_BITS
SCANNER = zbar.ImageScanner()
SCANNER.parse_config('enable')
# set QR codes to be read as pure binary
SCANNER.set_config(zbar.Symbol.QRCODE, zbar.Config.BINARY, 1)
PIPE = posixpath.join(posixpath.abspath(os.curdir), 'command.pipe')
URL = 'ipc://' + PIPE
logging.info('IPC pipe: %s, url: %s', PIPE, URL)

class Puff():
    '''
    data for a single transceive QR code

    unlike transmit() and receive(), which use different sized QR codes,
    transceive sends and receives codes of the same length:
    serial, SERIAL_BYTES bytes
    length, LENGTH_BYTES bytes
    chunk, CHUNKSIZE bytes
    hashed, HASHLENGTH bytes  # hash of what we saw from peer
    '''
    def __init__(self, data=b'', **kwargs):
        if data:
            offset = SERIAL_BYTES
            self.serial = int.from_bytes(data[:offset])
            length = int.from_bytes(data[offset:offset + LENGTH_BYTES])
            offset += LENGTH_BYTES
            self.chunk = data[offset:offset + length]
            offset += CHUNKSIZE
            self.hashed = data[offset:]
        else:
            self.serial = kwargs.get('serial', 0)
            self.chunk = kwargs.get('chunk', b'')
            self.hashed = kwargs.get('hashed', EMPTY_HASH)

    def __str__(self):
        return (
            f'<Puff serial={self.serial},'
            f' chunk={self.chunk};'
            f' hashed={self.hashed}>'
        )

    def update(self, **kwargs):
        '''
        fill in values that weren't available on instantiation
        '''
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logging.warning('not setting unknown attribute %s', key)

    def pack(self):
        '''
        pack data into correct form for QR code

        >>> len(Puff().pack()) == PACKET_LENGTH
        True
        '''
        return (self.serial.to_bytes(SERIAL_BYTES) +
            len(self.chunk).to_bytes(LENGTH_BYTES) +
            self.chunk.rjust(CHUNKSIZE, b'\0') +
            self.hashed)

    def bump_serial(self):
        '''
        increment serial number
        '''
        self.serial = (self.serial + 1) % SERIAL_MODULUS

    def checkhash(self):
        '''
        get hash digest with values of send_{serial,length,chunk}
        '''
        data = (
            self.serial.to_bytes(SERIAL_BYTES) +
            len(self.chunk).to_bytes(LENGTH_BYTES) +
            self.chunk
        )
        return chunkhash(data)

def transceive():  # pylint: disable=too-many-branches, too-many-statements
    '''
    listen on local socket for files to transmit, and watch for incoming
    barcodes from peer
    '''
    capture = cv2.VideoCapture(0)
    window = Tk()
    window.geometry('+0+0')
    label = Label(window, text='Transceiving...')
    label.pack()
    window.update()
    seen = lastseen = b''
    shown = None  # barcode being displayed
    send_document = received_document = None
    sent = Puff()
    received = None
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(URL)
        while capture.isOpened():
            if cv2.waitKey(1) & 0xff == ord('q'):
                break
            captured = capture.read()
            if captured[0]:
                cv2.imshow('frame captured', captured[1])
                cv2.moveWindow('frame captured', 1000, 0)
                seen = qrdecode(Image.fromarray(captured[1]))
                if seen and seen != lastseen:
                    received = Puff(data=seen)
                    logging.debug('seen: %r, received: %s', seen, received)
                    if received.hashed == sent.checkhash():
                        logging.debug('our last packet was received intact')
                        sent.bump_serial()
                    if received.chunk:
                        received_document = received_document or newpath()
                        with open(received_document, 'wb') as savedata:
                            savedata.seek(0, os.SEEK_END)
                            savedata.write(received.chunk)
                        sent.update(hashed=received.checkhash())
                    else:
                        received_document = None
                        received = None
                    lastseen = seen
            if socket.poll(1):
                send_document = socket.recv_string()
                sent.update(serial=0)
                logging.info('requested to send document %s', send_document)
            if send_document and shown != sent.pack():
                with open(send_document, 'rb') as senddata:
                    senddata.seek(sent.serial * CHUNKSIZE)
                    sent.update(chunk=senddata.read(CHUNKSIZE))
                if sent.chunk:
                    shown = qrshow(label, sent.pack())
                else:
                    logging.info('no more data')
                    send_document = None
                    sent.update(serial=0)
            elif received:
                shown = qrshow(label, sent.pack())
                received = None
    finally:
        socket.close()
        context.term()
        if posixpath.exists(PIPE):
            os.remove(PIPE)
        capture.release()
        cv2.destroyAllWindows()
        window.destroy()

def newpath():
    '''
    return pathspec for a new document
    '''
    return os.path.join('received', datetime.now().isoformat())

def sendfile(document):
    '''
    tell transceiver to send a document
    '''
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(URL)
        socket.send_string(document)
    finally:
        socket.close()
        context.term()

def transmit(document):
    '''
    send document to peer
    '''
    capture = cv2.VideoCapture(0)
    window = Tk()
    window.geometry('+0+0')
    label = Label(window, text='Transmitting...')
    label.pack()
    window.update()
    with open(document, 'rb') as senddata:
        serial = 0
        hashed = chunk = seen = lastseen = b''
        while capture.isOpened():
            if hashed == seen[SERIAL_BYTES:]:
                logging.debug('sending chunk %d', serial)
                chunk = senddata.read(CHUNKSIZE)
                if chunk:
                    codedata = serial.to_bytes(SERIAL_BYTES) + chunk
                    hashed = chunkhash(codedata)
                    qrshow(label, codedata)
                else:
                    logging.info('no more data')
            captured = capture.read()
            if captured[0]:
                cv2.imshow('frame captured', captured[1])
                cv2.moveWindow('frame captured', 1000, 0)
                seen = qrdecode(Image.fromarray(captured[1]))
                if seen and seen != lastseen:
                    logging.debug('seen: %s, hashed: %s, same: %s',
                                  seen, hashed,
                                  seen[SERIAL_BYTES:] == hashed)
                    if int.from_bytes(seen[:SERIAL_BYTES]) == serial and \
                            seen[SERIAL_BYTES:] == hashed:
                        lastseen = seen
                        serial = (serial + 1) % SERIAL_MODULUS
                    else:
                        logging.warning('bad data: %s', seen)
                        raise ValueError('bad data')
                elif not chunk:
                    logging.info('finished sending %s', document)
                    break
            if cv2.waitKey(1) & 0xff == ord('q'):
                break
    capture.release()
    cv2.destroyAllWindows()
    window.destroy()

def receive():
    '''
    receive document from peer
    '''
    capture = cv2.VideoCapture(0)
    window = Tk()
    window.geometry('+0+0')
    label = Label(window, text='Receiving...')
    label.pack()
    window.update()
    document = os.path.join('received', datetime.now().isoformat())
    serial = -1
    with open(document, 'wb') as received:
        seen = lastseen = b''
        while capture.isOpened():
            captured = capture.read()
            if captured[0]:
                cv2.imshow('frame captured', captured[1])
                cv2.moveWindow('frame captured', 800, 0)
                seen = qrdecode(Image.fromarray(captured[1]))
                if seen and seen != lastseen:
                    logging.debug('seen: %s', seen)
                    lastseen = seen
                    if int.from_bytes(seen[:SERIAL_BYTES]) == serial + 1:
                        received.write(seen[SERIAL_BYTES:])
                        hashed = chunkhash(seen)
                        codedata = seen[:SERIAL_BYTES] + hashed
                        qrshow(label, codedata)
                        serial = (serial + 1) % SERIAL_MODULUS
                    else:
                        logging.warning('packet out of order: %s', seen)
            if cv2.waitKey(1) & 0xff == ord('q'):
                break
    capture.release()
    cv2.destroyAllWindows()
    window.destroy()

def qrshow(label, data):
    '''
    display a QR code
    '''
    if data:
        try:
            image = qrcode.make(data)
        except ValueError:
            logging.error('cannot make %r into barcode', data)
            raise
        logging.debug('image type: %s', type(image))
        photo = Photo(image)
        label.configure(image=photo, data=None)
        label.image = photo  # claude: necessary to thwart garbage collection
        label.update()
        logging.debug('image: %s', image)
        code = qrdecode(image)
        logging.info('code: %r', code)
        return data
    return None

def qrdecode(image):
    r'''
    get data from QR code image

    >>> testdata = bytes(range(256))
    >>> qr_image = qrcode.make(testdata)
    >>> qrdecode(qr_image) == testdata
    True

    the following is from an error while transmitting /bin/bash

    >>> testdata = b'\x00\x00\x02\xef\x07\x00\x00\x00\xde\x00\x00\x00\x00\x00\
    ... \x00\x00\x00\x00\x00\x00\xb0>\x13\x00\x00\x00\x00\x00\x07\x00\x00\x00\
    ... \xdf\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb8>\x13\x00\x00\x00\
    ... \x00\x00\x07\x00\x00\x00\xe0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
    ... \x00\xc0>\x13\x00\x00\x00\x00\x00\x07\x00\x00\x00\xe1\x00\x00\x00\x00\
    ... \x00\x00\x00\x00\x00\x00\x00\xc8>\x13\x00\x00\x00\x00\x00\x07\x00\x00\
    ... \x00\xe2\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
    ... \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
    ... \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
    ... \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
    ... \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
    ... \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
    ... \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
    ... \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
    ... \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\
    ... \x00\x00\x00\x00'
    >>> len(testdata)  # should be 256 + 4-byte serial number prefix
    260
    >>> qr_image = qrcode.make(testdata)
    >>> qrdecode(qr_image) == testdata
    True
    '''
    try:
        pil = image.convert('L')  # to grayscale
    except AttributeError:  # cv2 frame is numpy array
        pil = Image.fromarray(image).convert('L')
    raw = pil.tobytes()
    zbar_image = zbar.Image(pil.width, pil.height, 'Y800', raw)
    SCANNER.scan(zbar_image)
    found = [(symbol.data, symbol.type) for symbol in zbar_image]
    if found:
        #logging.debug('scan results: %s', found)
        return found[0][0]
    return b''

def chunkhash(data):
    '''
    return binary hash of data
    '''
    return HASH(data).digest()

if __name__ == '__main__':
    callables = [
        (key, value) for key, value in locals().items() if callable(value)
    ]
    logging.debug('callables: %s', callables)
    if len(sys.argv) < 2:
        logging.error('Must specify command and optional args')
    elif sys.argv[1] not in ('transmit', 'receive', 'transceive', 'sendfile'):
        logging.error('%r not a recognized command', sys.argv[1])
    else:
        eval(sys.argv[1])(*sys.argv[2:])  # pylint: disable=eval-used
