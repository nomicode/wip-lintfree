#!/bin/sh -e

. test/lib/setup/linter.sh

# Using a pipe means the exit value of the first command will be ignored,
# allowing `obelist` to determine which severity level should result in an
# error
woke | strip-ansi |
    obelist parse --quiet --console --write "${lint_out}" \
        --error-on="notice" --parser="woke" --format="txt" -
