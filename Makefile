REQUISITE := python3-opencv python3-qrcode python3-qrtools \
 python3-tk python3-pil.imagetk
SCRIPTS := $(wildcard *.py)
DOCTESTS := $(SCRIPTS:.py=.doctest)
LINT := $(SCRIPTS:.py=.pylint)
send: smokesignal.py smokesignal.py
	./$+
receive: smokesignal.py
	./$+
prerequisites:
	sudo apt install $(REQUISITE)
%.pylint: %.py
	pylint $<
%.doctest: %.py
	python3 -m doctest $<
check: $(LINT) $(DOCTESTS)
