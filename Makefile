SHELL         = /bin/bash
SPHINXBUILD   = sphinx-build
APIBUILD      = sphinx-apidoc
COVERAGE      = coverage
UNITTEST      = python3 -m unittest
DOCSRCDIR     = doc-src
BUILDDIR      = docs
COVERAGEDIR   = $(BUILDDIR)/coverage
APIDIR        = $(DOCSRCDIR)/en/api
GETTEXT       = pygettext3
MSGMERGE      = msgmerge
MSGFMT        = msgfmt
LOCALE_DIR    = locale/po
INSTALL_DIR   = /usr/local/bin/
OS            = $(shell uname)
VERSION       = $(shell python3 -c "import catatom2osm; print(catatom2osm.__version__)")

# Internal variables.
PAPEROPT_a4     = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter
ALLSPHINXOPTS   = -d $(BUILDDIR)/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .
# the i18n builder cannot share the environment and doctrees with the others
I18NSPHINXOPTS  = $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .

.PHONY: help
help:  ## Show this help.
	@echo "Please use \`make <target>\` where <target> is one of"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

.PHONY: clean
clean:  ## Clean docs build directory
	rm -rf $(BUILDDIR)/*
	touch $(BUILDDIR)/.nojekyll

.PHONY: test
test:  ## Run unit tests
	$(UNITTEST) discover

.PHONY: coverage
coverage:  ## Make coverage report files
	$(COVERAGE) run --source=. test/unittest_main.py discover
	$(COVERAGE) report
	$(COVERAGE) html
	@echo
	@echo "Coverage finished. The HTML pages are in $(COVERAGEDIR)."

.PHONY: api
api:  ## Make autodoc files
	$(APIBUILD) -f -e -o $(APIDIR) .
	@echo
	@echo "API autodoc finished. The HTML pages are in $(APIDIR)."

.PHONY: html
html:  ## Make documentation html files
	rm -rf $(DOCSRCDIR)/es/api/*.rst
	for f in $(DOCSRCDIR)/en/api/*.rst; do \
		echo ".. include:: ../../en/api/$$(basename $$f)" > "$(DOCSRCDIR)/es/api/$$(basename $$f)"; \
	done
	cd $(DOCSRCDIR) && make html

.PHONY: msg
msg:  ## Build translations file
	$(GETTEXT) -o $(LOCALE_DIR)/messages.pot catatom2osm
	$(MSGMERGE) -U $(LOCALE_DIR)/es/LC_MESSAGES/catatom2osm.po $(LOCALE_DIR)/messages.pot
	$(MSGFMT) $(LOCALE_DIR)/es/LC_MESSAGES/catatom2osm.po -o $(LOCALE_DIR)/es/LC_MESSAGES/catatom2osm.mo
	$(MSGFMT) $(LOCALE_DIR)/es/LC_MESSAGES/argparse.po -o $(LOCALE_DIR)/es/LC_MESSAGES/argparse.mo
	@echo
	@echo "Translation finished. The language files are in $(LOCALE_DIR)."

.PHONY: install
install:  ## Create application simbolic link
	@cp $(shell pwd)/bin/run.sh $(INSTALL_DIR)/catatom2osm
	@chmod +x $(INSTALL_DIR)/catatom2osm
	@echo "Created script $(INSTALL_DIR)/catatom2osm"

.PHONY: uninstall
uninstall:  ## Remove application simbolic link
	@rm $(INSTALL_DIR)/catatom2osm

all: clean coverage api html msg  ## Do clean, api, coverage, html and msg
.PHONY: all

.PHONY: check
check:   ## Show the changes that the code formatters would apply.
	black .
	isort --diff .

.PHONY: format
format:   ## Run code formatters and apply it's changes.
	black .
	isort -y .

.PHONY: style
style:   ## Check code styling.
	flake8
	pydocstyle
	isort --check-only -rc .

.PHONY: build
build:  ## Build docker image
	@docker build -t catatom2osm .

.PHONY: build-dev
build-dev:  ## Build docker development image
	@docker build -t catatom2osm:dev --build-arg APP_ENV=dev .

.PHONY: run
run: build-dev  ## Run a Docker container to run the app
	@mkdir -p results
	@docker run --rm -it -v $(PWD):/opt/CatAtom2Osm -v $(PWD)/results:/catastro catatom2osm:dev

.PHONY: shell
shell: build-dev  ## Run a Docker container for development
	@mkdir -p results
	@docker run --rm -it -v $(PWD):/opt/CatAtom2Osm -v $(PWD)/results:/catastro -w /opt/CatAtom2Osm catatom2osm:dev

.PHONY: dtest
dtest:  ## Run a Docker container for testing
	@docker run --rm -it -v $(PWD):/opt/CatAtom2Osm -v $(PWD)/results:/catastro -w /opt/CatAtom2Osm catatom2osm:dev make test

.PHONY: publish
publish: build dtest  ## Push last version to GitHub and Docker Hub
	@echo $(VERSION)
	@echo "Pulsa una tecla para continuar"
	@read
	@git tag -f -a v$(VERSION) -m "Version $(VERSION)"
	@git push -f origin master v$(VERSION)
	@docker tag catatom2osm:latest egofer/catatom2osm:latest
	@docker tag catatom2osm:latest egofer/catatom2osm:$(VERSION)
	@docker push egofer/catatom2osm
	@docker push egofer/catatom2osm:$(VERSION)
