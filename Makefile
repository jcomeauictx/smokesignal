SHELL := /bin/bash
REQUIRED := python3-opencv python3-qrcode python3-qrtools \
 python3-tk python3-pil.imagetk python3-pyzbar python3-zbar
PKGMGR := $(word 1, $(shell which apt apt-get apk yum dnf 2>/dev/null))
INSTALL := install
ifeq ($(notdir $(PKGMGR)),apk)
REQUIRED := py3-qrcode python3-tkinter py3-pillow py3-pyzbar py3-zbar
INSTALL := add
endif
SCRIPTS := $(wildcard *.py)
DOCTESTS := $(SCRIPTS:.py=.doctest)
LINT := $(SCRIPTS:.py=.pylint)
ifneq ($(SHOWENV),)
export
endif
send: smokesignal.py /bin/bash
	./$+
receive: smokesignal.py
	./$+
requirements:
	sudo $(PKGMGR) $(INSTALL) $(REQUIRED)
%.pylint: %.py
	pylint $<
%.doctest: %.py
	python3 -m doctest $<
check: $(LINT) $(DOCTESTS)
env:
ifeq ($(SHOWENV),)
	$(MAKE) SHOWENV=1 $@
else
	$@
endif
