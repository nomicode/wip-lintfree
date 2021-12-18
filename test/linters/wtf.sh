#!/bin/sh -e

. test/lib/setup/linter.sh

run_wtf() {
    # This program is relatively slow, so we run it in parallel
    test/lib/tools/find-all-files.sh |
        xargs parallel-moreutils test/wrappers/wtf.sh --
}

# Using a pipe means the exit value of the first command will be ignored,
# allowing `obelist` to determine which severity level should result in an
# error
output="$(mktemp)"
run_wtf 2>"${output}"
obelist parse --quiet --console --write "${lint_out}" \
    --error-on="notice" --parser="wtf" --format="txt" - <"${output}"
rm -f "${output}"
