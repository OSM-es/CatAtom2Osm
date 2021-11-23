SHELL         = /bin/bash
SPHINXBUILD   = sphinx-build
APIBUILD      = sphinx-apidoc
COVERAGE      = coverage
UNITTEST      = python -m unittest
DOCSRCDIR     = doc-src
BUILDDIR      = docs
COVERAGEDIR   = $(BUILDDIR)/coverage
APIDIR        = $(DOCSRCDIR)/en/api
GETTEXT       = pygettext
MSGMERGE      = msgmerge
MSGFMT        = msgfmt
LOCALE_DIR    = locale/po
INSTALL_DIR   = /usr/local/bin/
OS            = $(shell uname)
VERSION       = $(shell catatom2osm -v 2>&1)

# Internal variables.
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .
# the i18n builder cannot share the environment and doctrees with the others
I18NSPHINXOPTS  = $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .

.PHONY: help
help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  clean      Clean docs build directory"
	@echo "  test       Run unit tests"
	@echo "  coverage   Make coverage report files"
	@echo "  api        Make autodoc files"
	@echo "  html       Make documentation html files"
	@echo "  msg        Build translations file"
	@echo "  install    Create application simbolic link"
	@echo "  uninstall  Remove application simbolic link"
	@echo "  all        clean api coverage html msg"
	@echo "  run        Run a Docker container for command line"
	@echo "  shell      Run a Docker container for developing"
	@echo "  publish    Push last version to Docker Hub"

.PHONY: clean
clean:
	rm -rf $(BUILDDIR)/*
	touch $(BUILDDIR)/.nojekyll

.PHONY: html
html:
	rm -rf $(DOCSRCDIR)/es/api/*.rst
	for f in $(DOCSRCDIR)/en/api/*.rst; do \
		echo ".. include:: ../../en/api/$$(basename $$f)" > "$(DOCSRCDIR)/es/api/$$(basename $$f)"; \
	done
	cd $(DOCSRCDIR) && make html

.PHONY: test
test:
ifeq (${OS},$(filter $(OS),Sierra Darwin))
	@source $(shell pwd)/pyqgismac.sh
endif
	$(UNITTEST) discover

.PHONY: coverage
coverage:
ifeq (${OS},$(filter $(OS),Sierra Darwin))
	@source $(shell pwd)/pyqgismac.sh
endif
	$(COVERAGE) run --source=. test/unittest_main.py discover
	$(COVERAGE) report
	$(COVERAGE) html
	@echo
	@echo "Coverage finished. The HTML pages are in $(COVERAGEDIR)."

.PHONY: api
api:
	$(APIBUILD) -f -e -o $(APIDIR) .
	@echo
	@echo "API autodoc finished. The HTML pages are in $(APIDIR)."

.PHONY: msg
msg:
	$(GETTEXT) -o $(LOCALE_DIR)/messages.pot *.py
	$(MSGMERGE) -U $(LOCALE_DIR)/es/LC_MESSAGES/catatom2osm.po $(LOCALE_DIR)/messages.pot
	$(MSGFMT) $(LOCALE_DIR)/es/LC_MESSAGES/catatom2osm.po -o $(LOCALE_DIR)/es/LC_MESSAGES/catatom2osm.mo
	$(MSGFMT) $(LOCALE_DIR)/es/LC_MESSAGES/argparse.po -o $(LOCALE_DIR)/es/LC_MESSAGES/argparse.mo
	@echo
	@echo "Translation finished. The language files are in $(LOCALE_DIR)."


.PHONY: install
install:
ifeq (${OS},$(filter $(OS),Sierra Darwin))
	@chmod +x pyqgismac.sh
	@chmod +x pyqgis3mac.sh
	@chmod +x catatom2osmmac
	@ln -sf $(shell pwd)/catatom2osmmac $(INSTALL_DIR)/catatom2osm
	@echo "Created symbolic link $(INSTALL_DIR)-->$(shell pwd)/catatom2osmmac"
else
	@chmod +x catatom2osm
	@ln -sf $(shell pwd)/catatom2osm $(INSTALL_DIR)/catatom2osm
	@echo "Created symbolic link $(INSTALL_DIR)-->$(shell pwd)/catatom2osm"
endif

.PHONY: uninstall
uninstall:
	@unlink /usr/local/bin/catatom2osm

all: clean coverage api html msg
.PHONY: all

.PHONY: run
run:
	@mkdir -p results
	@docker build -t catatom2osm .
	@docker run --rm -it -v $(PWD):/opt/CatAtom2Osm -v $(PWD)/results:/catastro catatom2osm

.PHONY: shell
shell:
	@mkdir -p results
	@docker build -t catatom2osm:dev --build-arg REQUISITES=requisites-dev.txt .
	@docker run --rm -it -v $(PWD):/opt/CatAtom2Osm -v $(PWD)/results:/catastro -w /opt/CatAtom2Osm catatom2osm:dev

.PHONY: publish
publish:
	@docker build -t catatom2osm .
	@echo $(VERSION)
	@echo "Pulsa una tecla para continuar"
	@read
	@docker tag catatom2osm:latest egofer/catatom2osm:latest
	@docker tag catatom2osm:latest egofer/catatom2osm:1.3.10
	@docker push -a egofer/catatom2osm
