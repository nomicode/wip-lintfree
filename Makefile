.EXPORT_ALL_VARIABLES:

.DEFAULT_GOAL = help

# ANSI codes
BOLD=[1m
DIM=[2m
ITALIC=[3m
RESET=[0m

VENV     := .venv
PATH     := $(VENV)/bin:$(PATH)
SUBMAKE  := $(MAKE) --no-print-directory
LINT_OUT := lint.tmp

define sh
@ printf "\e$(DIM)$$ %s\e$(RESET)\n" \
	"$$(echo $1 | sed -E 's,make -[^ ]+ ,make ,')" && \
	OBELIST_NO_ERROR="true" $1;
endef

.PHONY: help # Print this help message and exit
help:
	@ printf "\e$(BOLD)Targets:\e$(RESET)\n\n"
	@ @grep -E '^.PHONY:' $(shell printf "%s\n" $(MAKEFILE_LIST) | tac) | \
		grep "#" | sed 's,.*: ,,' | \
		awk 'BEGIN {FS = " # "}; {printf "  make %s,%s\n", $$1, $$2}' | \
		column -t -s ',' | \
		sed -E 's,(.*make )([^ ]+)( .*),\1\x1b$(ITALIC)\2\x1b$(RESET)\3,'

$(VENV):
	$(call sh,poetry install)
	@ $(SUBMAKE) venv-help

.PHONY: venv-help
venv-help:
	@ if test -z "${VIRTUAL_ENV}"; then \
		echo; \
		printf "Run \`\e[4mpoetry shell\e[0m\` to activate your "; \
		printf "Python virtual environment\n"; \
	fi

.PHONY: install # Install the Python package into a virtual environment
install: $(VENV)

install-clean:
	$(call sh,rm -rf $(VENV))

update-run:
	$(call sh,poetry update)

.PHONY: update # Update the Python package and reinstall
update: install-clean update-run install
	@ $(SUBMAKE) venv-help

.PHONY: wtf
wtf:
	@ test/linters/wtf.sh

.PHONY: lintspaces
lintspaces:
	@ test/linters/lintspaces.sh

.PHONY: ec
ec:
	@ test/linters/ec.sh

.PHONY: misspell
misspell:
	@ test/linters/misspell.sh

.PHONY: cspell
cspell:
	@ test/linters/cspell.sh

.PHONY: woke
woke:
	@ test/linters/woke.sh

.PHONY: proselint
proselint:
	@ test/linters/proselint.sh

.PHONY: lychee
lychee:
	@ test/linters/lychee.sh

.PHONY: markdown-link-check
markdown-link-check:
	@ test/linters/markdown-link-check.sh

.PHONY: markdownlint
markdownlint:
	@ test/linters/markdownlint.sh

.PHONY: prettier
prettier:
	@ test/linters/prettier.sh

.PHONY: yamllint
yamllint:
	@ test/linters/yamllint.sh || true

.PHONY: jscpd
jscpd: $(VENV)
	@ test/linters/jscpd.sh

.PHONY: shellcheck
shellcheck:
	@ test/linters/shellcheck.sh

.PHONY: shfmt
shfmt:
	@ test/linters/shfmt.sh

.PHONY: black
black: $(VENV)
	@ test/linters/black.sh

.PHONY: reorder-python-imports
reorder-python-imports: $(VENV)
	@ test/linters/reorder-python-imports.sh

.PHONY: prospector
prospector: $(VENV)
	@ test/linters/prospector.sh

.PHONY: flake8
flake8: $(VENV)
	@ test/linters/flake8.sh

.PHONY: pytest
pytest: $(VENV)
	@ test/linters/pytest.sh

.PHONY: codecov
codecov: $(VENV)
	@ test/linters/codecov.sh

.PHONY: lint-clean
lint-clean:
	@ rm -f $(LINT_OUT)

.PHONY: lint-output
lint-run: $(VENV) lint-clean
	$(call sh,$(SUBMAKE) wtf)
	$(call sh,$(SUBMAKE) lintspaces)
	$(call sh,$(SUBMAKE) ec)
	$(call sh,$(SUBMAKE) cspell)
	$(call sh,$(SUBMAKE) misspell)
	$(call sh,$(SUBMAKE) woke)
	$(call sh,$(SUBMAKE) proselint)
	$(call sh,$(SUBMAKE) lychee)
	$(call sh,$(SUBMAKE) markdown-link-check)
	$(call sh,$(SUBMAKE) markdownlint)
	$(call sh,$(SUBMAKE) prettier)
	$(call sh,$(SUBMAKE) yamllint)
	$(call sh,$(SUBMAKE) jscpd)
	$(call sh,$(SUBMAKE) shellcheck)
	$(call sh,$(SUBMAKE) shfmt)
	$(call sh,$(SUBMAKE) black)
	$(call sh,$(SUBMAKE) reorder-python-imports)
	$(call sh,$(SUBMAKE) prospector)
	$(call sh,$(SUBMAKE) flake8)
	$(call sh,$(SUBMAKE) pytest)
	$(call sh,$(SUBMAKE) codecov)

.PHONY: lint-format
lint-process: lint-run
	@ if test -s "$(LINT_OUT)"; then \
		obelist format --error-on="notice" "$(LINT_OUT)"; \
	fi

.PHONY: lint # Run lint checks
lint: lint-process
	@ $(SUBMAKE) lint-clean

# TODO: Not implemented yet
.PHONY: format # Run all available auto-formatters
format:
	@ echo shellcheck --format=diff
	@ echo black

.PHONY: clean # Reset the build cache
clean: install-clean
