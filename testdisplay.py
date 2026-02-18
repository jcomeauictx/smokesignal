#!/usr/bin/python3
'''
test display of QR code
'''
import sys, qrcode, logging
from qrtools import QR

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

def test(text):
    '''
    display a QR code
    '''
    image = qrcode.make(text)
    qrtools = QR(data=text)
    logging.debug('qrtools: %s', qrtools)
    image.show()
    code = qrtools.decode(image=image)
    logging.info('qrtools: %s, code: %r', qrtools, code)

if __name__ == '__main__':
    test(' '.join(sys.argv[1:]) or 'This is a test of smokesignal')
