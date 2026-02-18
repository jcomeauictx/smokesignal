#!/usr/bin/python3
'''
test display of QR code
'''
import sys, qrcode

def test(text):
    '''
    display a QR code
    '''
    image = qrcode.make(text)
    image.show()
    input()

if __name__ == '__main__':
    test(' '.join(sys.argv[1:]) or 'This is a test of smokesignal')
