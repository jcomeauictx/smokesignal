REQUISITE := python3-opencv python3-qrcode python3-qrtools python3-tk
all: smokesignal.py
	./$<
prerequisites:
	sudo apt install $(REQUISITE)
