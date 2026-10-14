SHELL := /usr/bin/env bash
.SHELLFLAGS := -eo pipefail -c

KAK ?= kak
THEMES := $(notdir $(basename $(wildcard colors/*.kak)))

.PHONY: help all generate validate install clean list

help:
	@echo "justaperlhacker/kakoune-themes"
	@echo
	@echo "  make generate           Regenerate colors/*.kak from palettes/"
	@echo "  make validate           Source every theme with kak (syntax check)"
	@echo "  make install            Install colors into \$$XDG_CONFIG_HOME/kak/colors"
	@echo "  make list               List available themes"
	@echo "  make clean              Remove generated themes"
	@echo
	@echo "  PREFIX=... make install Override the Kakoune config directory"

all: generate

generate:
	python3 scripts/gen_themes.py

validate: colors
	@fail=0; for f in colors/*.kak; do \
		if ! $(KAK) -n -ui dummy -e "$$(printf 'source %s\nquit' "$$PWD/$$f")" >/dev/null 2>&1; then \
			echo "FAIL $$f"; fail=1; \
		fi; \
	done; \
	if [ $$fail -eq 0 ]; then echo "All themes OK"; else exit 1; fi

install:
	@dest="$${PREFIX:-$${XDG_CONFIG_HOME:-$$HOME/.config}/kak}/colors"; \
	mkdir -p "$$dest"; \
	cp colors/*.kak "$$dest"; \
	echo "Installed $$(ls colors/*.kak | wc -l) themes into $$dest"

list:
	@for t in $(THEMES); do echo $$t; done

clean:
	rm -f colors/*.kak
