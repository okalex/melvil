BLENDER_VERSION ?= 5.0
BLENDER_ADDONS_DIR ?= $(HOME)/Library/Application Support/Blender/$(BLENDER_VERSION)/extensions/user_default
ADDON_NAME := melvil
ADDON_SRC := src

.PHONY: install uninstall test sync

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
