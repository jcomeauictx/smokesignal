SHELL := /bin/bash
GITPREFIX ?= $(dir $(shell git remote get-url origin))
PYTHON ?= $(word 1, $(shell which python3 python false 2>/dev/null))
PYLINT ?= $(word 1, $(shell which pylint pylint3 false 2>/dev/null))
JSREQUIRED := qrcodejs jsQR html5-qrcode
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
dependencies:
	sudo $(PKGMGR) $(INSTALL) $(REQUIRED)
	cd .. && for requirement in $(JSREQUIRED); do \
	 if [ -d $$requirement ]; then \
	  (cd $$requirement && git pull); \
	 else \
	  git clone $(GITPREFIX)$$requirement; \
	 fi; \
	done
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
droplet:
	@if ! ping -c 1 droplet; then \
	 echo See section quickstart of README.md >&2; \
	 false; \
	fi
	ssh root@droplet apt update
	ssh root@droplet apt install -y make git
	ssh root@droplet 'id $(USER) || useradd -m $(USER)'
	ssh root@droplet '[ -d ~$(USER)/.ssh ] || \
	 mkdir -m 0700 ~$(USER)/.ssh && chown $(USER):$(USER) ~$(USER)/.ssh'
	ssh root@droplet '[ -f ~$(USER)/.ssh/authorized_keys ] || \
	 cp -a .ssh/authorized_keys ~$(USER)/.ssh/ && \
	 chown $(USER):$(USER) ~$(USER)/.ssh/authorized_keys'
	ssh droplet mkdir -p src/jcomeauictx
	ssh droplet '[ -f .ssh/id_rsa.pub ] || ssh-keygen -t rsa \
	 -f .ssh/id_rsa -N ""'
	@ssh droplet '[ -d src/jcomeauictx/smokesignal ] || \
	 git clone $(GITPREFIX)/smokesignal || \
	 echo "you may need to add your droplet key to your git repo" >&2; \
	 cat .ssh/id_rsa.pub; \
	 false'

env:
ifeq ($(SHOWENV),)
	$(MAKE) SHOWENV=1 $@
else
	$@
endif
