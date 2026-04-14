BLENDER_VERSION ?= 5.0
BLENDER_ADDONS_DIR ?= $(HOME)/Library/Application Support/Blender/$(BLENDER_VERSION)/extensions/user_default
ADDON_NAME := melvil
ADDON_SRC := src

ADDON_VERSION := $(shell grep '^version' $(ADDON_SRC)/blender_manifest.toml | head -1 | sed 's/.*= *"\(.*\)"/\1/')

.PHONY: install uninstall test sync package

## Install a copy of the add-on into Blender's addons directory
install:
	mkdir -p "$(BLENDER_ADDONS_DIR)/$(ADDON_NAME)"
	cp -r $(ADDON_SRC)/ "$(BLENDER_ADDONS_DIR)/$(ADDON_NAME)"
	@echo "Installed $(ADDON_NAME) to $(BLENDER_ADDONS_DIR)"

## Remove the add-on from Blender's addons directory
uninstall:
	rm -rf "$(BLENDER_ADDONS_DIR)/$(ADDON_NAME)"
	@echo "Uninstalled $(ADDON_NAME) from $(BLENDER_ADDONS_DIR)"

## Run the test suite
test:
	uv run pytest

## Sync dependencies
sync:
	uv sync

## Build the icon atlas from Blender's SVG source
icons:
	DYLD_FALLBACK_LIBRARY_PATH="$$(brew --prefix)/lib" uv run python scripts/build_icon_atlas.py --tag v$(BLENDER_VERSION).0

## Build a distributable zip for Blender installation
package:
	rm -rf dist/$(ADDON_NAME) dist/$(ADDON_NAME)-$(ADDON_VERSION).zip
	mkdir -p dist/$(ADDON_NAME)
	rsync -a --exclude '*.DS_Store' --exclude '__pycache__' --exclude '*.pyc' $(ADDON_SRC)/ dist/$(ADDON_NAME)/
	cd dist && zip -r $(ADDON_NAME)-$(ADDON_VERSION).zip $(ADDON_NAME)
	rm -rf dist/$(ADDON_NAME)
	@echo "Built dist/$(ADDON_NAME)-$(ADDON_VERSION).zip"
