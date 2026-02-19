REQUISITE := python3-opencv python3-qrcode python3-qrtools
all: smokesignal.py
	./$<
prerequisites:
	sudo apt install $(REQUISITE)
