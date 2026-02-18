#!/usr/bin/python3
'''
test read from camera
'''
import sys, cv2

def test():
    '''
    open camera and read a single frame
    '''
    capture = cv2.VideoCapture(0)
    if capture.isOpened():
        captured = capture.read()
        if captured[0]:
            cv2.imshow('frame captured', captured[1])
            input()

if __name__ == '__main__':
    test()
