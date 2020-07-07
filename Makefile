PY2 = python
PY3 = python3
PY = $(PY2)
TWINE = twine

XARGS = xargs
GREP = grep
FIND = find
SED = sed
TR = tr
RM = rm
PACKAGE_NAME = vishop
METADATA_FILE = $(PACKAGE_NAME)/__about__.py
PACKAGE_VERSION = $(shell \
	$(SED) -n -E "s/__version__ = [\"']([^\"']+)[\"']/\1/p" $(METADATA_FILE))
DIST_DIR = dist
DIST_FILES = $(wildcard $(DIST_DIR)/$(PACKAGE_NAME)-$(PACKAGE_VERSION)*)

all: clean build

build: py2dist py3dist

py2dist:
	$(PY2) setup.py sdist bdist_wheel

py3dist:
	$(PY3) setup.py sdist bdist_wheel

check:
	$(TWINE) check $(DIST_DIR)/$(PACKAGE_NAME)-$(PACKAGE_VERSION)*

publish: all check
	$(TWINE) upload $(DIST_FILES)

pkg_version:
	@echo $(PACKAGE_VERSION)

clean:
	$(GREP) '/$$' .gitignore \
		| $(XARGS) -I{} echo "\\! -path '*/{}*'" \
		| $(TR) $$'\n' ' ' | $(XARGS) $(FIND) . -name '*.pyc' \
		| $(XARGS) -n1 $(RM)
	$(PY) setup.py clean

