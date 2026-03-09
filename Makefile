SHELL := /bin/bash
WHICH ?= type -p
GITPREFIX ?= $(dir $(shell git remote get-url origin))
PYTHON ?= $(word 1, $(shell which python3 python 2>/dev/null))
PYTHON_PKG := python3
PYTHON_APK := python3
PYLINT ?= $(word 1, $(shell which pylint pylint3 2>/dev/null))
PYLINT_PKG := pylint
PYLINT_APK := py3-pylint
FIREFOX ?= $(word 1, $(shell which firefox 2>/dev/null))
FIREFOX_PKG := firefox-esr
FIREFOX_APK :=  # not needed on iSH (but is actually available!)
XAUTH := $(word 1, $(shell which xauth))
XAUTH_PKG := xauth
XAUTH_APK :=  # also not needed on iSH, but available
REPO := $(notdir $(CURDIR))
COMMANDS := PYTHON PYLINT FIREFOX XAUTH
JSREQUIRED := qrcodejs jsQR html5-qrcode
REQUIRED := python3-opencv python3-qrcode python3-qrtools \
 python3-tk python3-pil.imagetk python3-zbar python3-zmq
YES := -y
PKGMGR := $(word 1, $(shell which apk apt apt-get yum dnf 2>/dev/null))
INSTALL := install
PACKAGES := $(foreach COMMAND, $(COMMANDS), $($(COMMAND)_PKG))
ifeq ($(notdir $(PKGMGR)),apk)
REQUIRED := py3-qrcode python3-tkinter py3-pillow py3-pyzbar py3-zbar \
 py3-pyzmq
INSTALL := add
YES :=
PACKAGES := $(foreach COMMAND, $(COMMANDS), $($(COMMAND)_APK))
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
	cd .. && for requirement in $(JSREQUIRED); do \
	 if [ -d $$requirement ]; then \
	  (cd $$requirement && git pull); \
	 else \
	  git clone $(GITPREFIX)$$requirement; \
	 fi; \
	done
dependencies.root:
	$(PKGMGR) $(YES) $(INSTALL) $(REQUIRED) $(PACKAGES)
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
	if [ "$$(which firefox)" ]; then \
	 firefox http://127.0.0.1:8080/; \
	else \
	 echo point your browser to http://127.0.0.1:8080/ >&2; \
	fi
droplet:
	@if ! ping -c 1 droplet; then \
	 echo See section quickstart of README.md >&2; \
	 false; \
	fi
	ssh root@droplet apt update
	ssh root@droplet apt -y upgrade
	ssh root@droplet apt install -y make git
	ssh root@droplet 'id $(USER) || \
	 useradd --create-home --shell /bin/bash $(USER)'
	ssh root@droplet '[ -d ~$(USER)/.ssh ] || \
	 mkdir -m 0700 ~$(USER)/.ssh && chown $(USER):$(USER) ~$(USER)/.ssh'
	ssh root@droplet '[ -f ~$(USER)/.ssh/authorized_keys ] || \
	 cp -a .ssh/authorized_keys ~$(USER)/.ssh/ && \
	 chown $(USER):$(USER) ~$(USER)/.ssh/authorized_keys'
	ssh $(USER)@droplet mkdir -p src/jcomeauictx
	ssh $(USER)@droplet '[ -f .ssh/id_rsa.pub ] || ssh-keygen -t rsa \
	 -f .ssh/id_rsa -N ""'
	ssh $(USER)@droplet 'grep -q "^github.com " .ssh/known_hosts || \
	 ssh-keyscan github.com >> .ssh/known_hosts'
	ssh $(USER)@droplet 'if [ -d src/jcomeauictx/$(REPO) ]; then \
	 (cd src/jcomeauictx/$(REPO) && git pull); else \
	 (cd src/jcomeauictx && git clone $(GITPREFIX)$(REPO)) || \
	 (echo "you may need to add your droplet key to your git repo" >&2; \
	 cat ~/.ssh/id_rsa.pub; \
	 false); \
	 fi'
	ssh root@droplet 'cd ~$(USER)/src/jcomeauictx/$(REPO) && \
	 make dependencies.root'
	ssh $(USER)@droplet 'cd ~$(USER)/src/jcomeauictx/$(REPO) && \
	 make dependencies'
	ssh $(USER)@droplet 'cd ~$(USER)/src/jcomeauictx/$(REPO) && \
	 wget -O- http://127.0.0.1:8080/README.md > /dev/null 2>&1 \
	 || setsid -f make wsgi < /dev/null > wsgi.log 2>&1'
	ssh -Y $(USER)@droplet 'cd ~$(USER)/src/jcomeauictx/$(REPO) && \
	 setsid -f firefox http://127.0.0.1:8080/ < /dev/null > /dev/null 2>&1; \
	 sleep 1; tail -n 100 -f wsgi.log'
env:
ifeq ($(SHOWENV),)
	$(MAKE) SHOWENV=1 $@
else
	$@
endif
