#!/usr/bin/python3
'''
test display of QR code
'''
import sys, qrcode, logging
from zbar import ImageScanner

logging.basicConfig(level=logging.DEBUG if __debug__ else logging.INFO)

def test(text):
    '''
    display a QR code
    '''
    image = qrcode.make(text)
    image.show()
    barcode = ImageScanner.scan(image)
    logging.info('barcode: %r', barcode)

if __name__ == '__main__':
    test(' '.join(sys.argv[1:]) or 'This is a test of smokesignal')
