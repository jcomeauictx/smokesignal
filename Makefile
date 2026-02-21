SHELL := /bin/bash
REQUISITE := python3-opencv python3-qrcode python3-qrtools \
 python3-tk python3-pil.imagetk
PKGMGR := $(word 1, $(shell which apt apt-get apk yum dnf 2>/dev/null))
INSTALL := install
ifeq ($(notdir $(PKGMGR)),apk)
REQUISITE := $(subst python3, py3, $(REQUISITE))
INSTALL := add
endif
SCRIPTS := $(wildcard *.py)
DOCTESTS := $(SCRIPTS:.py=.doctest)
LINT := $(SCRIPTS:.py=.pylint)
ifneq ($(SHOWENV),)
export
endif
send: smokesignal.py smokesignal.py
	./$+
receive: smokesignal.py
	./$+
prerequisites:
	sudo $(PKGMGR) $(INSTALL) $(REQUISITE)
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
