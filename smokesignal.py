#!/usr/bin/python3
'''
communicate visually with another computer using QR codes

QR codes sent and received start with a hash of the chunk
last received; the remainder is the chunk being sent
'''
# pylint: disable=c-extension-no-member  # for cv2
import sys, os, logging  # pylint: disable=multiple-imports
from datetime import datetime
from hashlib import sha256
from tkinter import Tk, Label
try:
    import cv2
except ImportError:
    pass  # not available on iSH
import qrcode, zbar  # pylint: disable=multiple-imports
from PIL import Image
from PIL.ImageTk import PhotoImage as Photo

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

HASH = sha256
HASHLENGTH = len(HASH(b'').digest())
EMPTY_HASH = bytes(HASHLENGTH)
CHUNKSIZE = 128
SERIAL_BITS = 32
SERIAL_BYTES = SERIAL_BITS // 8
SERIAL_MODULUS = 1 << SERIAL_BITS
SCANNER = zbar.ImageScanner()
SCANNER.parse_config('enable')
# set QR codes to be read as pure binary
SCANNER.set_config(zbar.Symbol.QRCODE, zbar.Config.BINARY, 1)

def transmit(document):
    '''
    send document to peer
    '''
    capture = cv2.VideoCapture(0)
    window = Tk()
    window.geometry('+0+0')
    label = Label(window, text='Starting...')
    label.pack()
    window.update()
    with open(document, 'rb') as senddata:
        serial = 0
        hashed = chunk = seen = lastseen = b''
        while capture.isOpened():
            if hashed == seen[:SERIAL_BYTES]:
                chunk = senddata.read(CHUNKSIZE)
                codedata = serial.to_bytes(SERIAL_BYTES) + chunk
                hashed = chunkhash(codedata)
                qrshow(label, codedata)
            captured = capture.read()
            if captured[0]:
                cv2.imshow('frame captured', captured[1])
                cv2.moveWindow('frame captured', 800, 0)
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
                if seen != lastseen:
                    logging.debug('seen: %s', seen)
                    lastseen = seen
                    if int.from_bytes(seen[:SERIAL_BYTES]) == serial + 1:
                        received.write(seen[SERIAL_BYTES:])
                        hashed = chunkhash(seen[SERIAL_BYTES:])
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
        image = qrcode.make(data)
        logging.debug('image type: %s', type(image))
        photo = Photo(image)
        label.configure(image=photo, data=None)
        label.image = photo  # claude: necessary to thwart garbage collection
        label.update()
        logging.debug('image: %s', image)
        code = qrdecode(image)
        logging.info('code: %r', code)

def qrdecode(image):
    '''
    get data from QR code image

    >>> testdata = bytes(range(256))
    >>> qr_image = qrcode.make(testdata)
    >>> qrdecode(qr_image) == testdata
    True
    '''
    try:
        pil = image.convert('L')  # to grayscale
    except AttributeError:
        pil = Image.fromarray(image).convert('L')
    raw = pil.tobytes()
    zbar_image = zbar.Image(pil.width, pil.height, 'Y800', raw)
    scanner.scan(zbar_image)
    found = [(symbol.data, symbol.type) for symbol in zbar_image]
    if found:
        logging.debug('scan results: %s', found)
        return found[0][0].encode('latin-1')
    return b''

def chunkhash(data):
    '''
    return binary hash of data
    '''
    return HASH(data).digest()

if __name__ == '__main__':
    # if no document specified, send nothing, just receive
    if len(sys.argv) > 1:
        transmit(sys.argv[1])
    else:
        receive()
