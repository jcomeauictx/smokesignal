#!/usr/bin/python3
'''
communicate visually with another computer using QR codes
'''
import sys, logging  # pylint: disable=multiple-imports
import qrcode, cv2  # pylint: disable=multiple-imports
from tkinter import Tk, Label
from PIL.ImageTk import PhotoImage as Photo
from qrtools import QR

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

def send(document):
    '''
    send document to peer
    '''
    capture = cv2.VideoCapture(0)
    with open(document) as data:
        chunked = chunks(data.read())
        while capture.isOpened():
            show_qr(next(chunked))
            captured = capture.read()
            if captured[0]:
                cv2.imshow('frame captured', captured[1])
            if cv2.waitKey(1) & 0xff == ord('q'):
                break
    capture.release()
    cv2.destroyAllWindows()

def show_qr(text):
    '''
    display a QR code
    '''
    image = qrcode.make(text)
    qrtools = QR(data=text)
    logging.debug('qrtools: %s', vars(qrtools))
    image.show()
    code = qrtools.decode(image=image)
    logging.info('qrtools: %s, code: %r', vars(qrtools), code)

def chunks(data, size=128):
    '''
    break a large file into chunks
    '''
    for i in range(0, len(data), size):
        yield data[i:i + size]

if __name__ == '__main__':
    # if no document specified, send this file itself
    send((sys.argv[1:] + [sys.argv[0]])[0])

