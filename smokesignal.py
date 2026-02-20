#!/usr/bin/python3
'''
communicate visually with another computer using QR codes
'''
# pylint: disable=c-extension-no-member  # for cv2
import sys, os, logging  # pylint: disable=multiple-imports
from datetime import datetime
from hashlib import sha256
from tkinter import Tk, Label
import qrcode, cv2  # pylint: disable=multiple-imports
from PIL import Image
from PIL.ImageTk import PhotoImage as Photo
from qrtools import QR

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

HASH = sha256
HASHLENGTH = len(HASH(b'').digest())
EMPTY_HASH = bytes(HASHLENGTH)
CHUNKSIZE = 128

def send(document=None):
    '''
    exchange documents with peer

    QR codes sent and received start with a hash of the chunk
    last received; the remainder is the chunk being sent
    '''
    capture = cv2.VideoCapture(0)
    window = Tk()
    window.geometry('+0+0')
    label = Label(window, text='Starting...')
    label.pack()
    window.update()
    document = document or os.devnull
    with open(document, 'rb') as senddata:
        chunk = seen = lastseen = b''
        while capture.isOpened():
            if chunk == seen:
                chunk = senddata.read(CHUNKSIZE)
                qrshow(label, chunk)
            captured = capture.read()
            if captured[0]:
                cv2.imshow('frame captured', captured[1])
                cv2.moveWindow('frame captured', 800, 0)
                seen = qrdecode(Image.fromarray(captured[1]))
                if seen != lastseen:
                    logging.debug('seen: %s, chunk: %s, same: %s',
                                  seen, chunk, seen == chunk)
                    lastseen = seen
                elif not chunk:
                    break
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

    qrtools tries to return data as string, presumably UTF8, and
    only returns bytes if that fails.

    can't find documentation on data_type parameter
    '''
    qr = QR(data='', data_type='bytes', add_bom=False)
    decoded = qr.decode(image=image)
    #logging.debug('decoded: %r, qr: %s', decoded, vars(qr))
    if decoded:
        if hasattr(qr.data, 'decode'):
            logging.debug('QR code data was returned as %d bytes',
                          len(qr.data))
            return qr.data
        else:
            logging.debug('QR code data was returned as string %r', qr.data)
            for encoding in ('big5', 'utf-8', 'latin-1'):
                try:
                    encoded = qr.data.encode(encoding)
                    return encoded
                except UnicodeEncodeError:
                    continue
    return None

def hash(data):
    '''
    return binary hash of data
    '''
    return HASH(data).digest()

if __name__ == '__main__':
    # if no document specified, send nothing, just receive
    send(sys.argv[1] if len(sys.argv) > 1 else None)
