#!/usr/bin/python3
'''
communicate visually with another computer using QR codes
'''
# pylint: disable=c-extension-no-member  # for cv2
import sys, logging  # pylint: disable=multiple-imports
from tkinter import Tk, Label
import qrcode, cv2  # pylint: disable=multiple-imports
from PIL import Image
from PIL.ImageTk import PhotoImage as Photo
from qrtools import QR

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

def send(document):
    '''
    send document to peer
    '''
    capture = cv2.VideoCapture(0)
    window = Tk()
    window.geometry('+0+0')
    label = Label(window, text='Starting...')
    label.pack()
    window.update()
    with open(document, 'rb') as data:
        chunked = chunks(data.read())
        chunk = seen = None
        while capture.isOpened():
            if chunk == seen:
                chunk = next(chunked, None)
                qrshow(label, chunk)
            captured = capture.read()
            if captured[0]:
                cv2.imshow('frame captured', captured[1])
                cv2.moveWindow('frame captured', 800, 0)
                seen = qrdecode(Image.fromarray(captured[1]))
                logging.debug('seen: %s', seen)
            if cv2.waitKey(1) & 0xff == ord('q'):
                break
    capture.release()
    cv2.destroyAllWindows()
    window.destroy()

def qrshow(label, text):
    '''
    display a QR code
    '''
    if text:
        image = qrcode.make(text)
        photo = Photo(image)
        qr = QR(data=text)
        logging.debug('qr: %s', vars(qr))
        label.configure(image=photo, text=None)
        label.image = photo  # claude: necessary to thwart garbage collection
        label.update()
        logging.debug('image: %s', image)
        code = qrdecode(image)
        logging.info('code: %r', code)

def qrdecode(image):
    '''
    get text/data from QR code image
    '''
    qr = QR(data=b'')
    decoded = qr.decode(image=image)
    #logging.debug('decoded: %r, qr: %s', decoded, vars(qr))
    return qr.data.encode('latin-1') if decoded else None

def chunks(data, size=128):
    '''
    break a large file into chunks
    '''
    for i in range(0, len(data), size):
        yield data[i:i + size]

if __name__ == '__main__':
    # if no document specified, send this file itself
    send((sys.argv[1:] + [sys.argv[0]])[0])
