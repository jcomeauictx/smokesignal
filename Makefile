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
DRYRUN ?= --dry-run
DELETE ?= --delete
ifneq ($(SHOWENV),)
export
endif
default: wsgi
transceive: smokesignal.py
	./$< $@
transmit: smokesignal.py /bin/bash
	./$< $@ $(word 2, $+)
receive: smokesignal.py
	./$< $@
requirements:
	sudo $(PKGMGR) $(INSTALL) $(REQUIRED)
%.pylint: %.py
	pylint $<
%.doctest: %.py
	python3 -m doctest $<
check: $(LINT) $(DOCTESTS)
syncpeer:
	rsync -avcz $(DRYRUN) $(DELETE) \
	 --exclude '.git' \
	 --exclude 'sent' \
	 --exclude 'received' \
	 --exclude '__pycache__' \
	 . peer:$(PWD)/
wsgi: wsgi.py
	python3 $<
uwsgi: wsgi.py
	$@ --http :8080 --wsgi-file $< --callable application
edit:
	vi wsgi.py smokesignal.{html,js,css}
view:
	xdg-open http://127.0.0.1:8080/
env:
ifeq ($(SHOWENV),)
	$(MAKE) SHOWENV=1 $@
else
	$@
endif
