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
    while capture.isOpened():
        captured = capture.read()
        if captured[0]:
            cv2.imshow('frame captured', captured[1])
        if cv2.waitKey(1) & 0xff == ord('q'):
            break
    capture.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    test()
