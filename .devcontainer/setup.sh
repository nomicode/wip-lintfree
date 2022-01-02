#!/bin/sh -e

# TODO: Turn this into a makefile so I can see what's happening during the
# build.
#
# More importantly, I can define targets for individual tags. The targets can
# then specify what they want installed. If I set the dependency chains up
# properly, this will mean an efficient way of building exactly what is needed
# for each specific tag without the need for code duplication or a complex web
# of multiple install scripts.

usermod --shell /bin/bash root

sudo groupadd docker
sudo usermod -aG docker root

# Temporary hack to force the `root` user to pick up environment variables set
# by the Dockerfile when the container is crated. Funnily enough, the
# environment variables set in the Dockerfile are picked up during image
# creation.
#
# TODO: Figure out why the `root` user does not pick up these environment
# variables
cat >>~/.bashrc <<EOF

set -a
. /etc/environment >> ~/.bashrc
set +a
EOF

apk update
apk upgrade

apk add --no-cache \
    alpine-sdk

# I thought this would fix it, but it doesn't
apk add --no-cache linux-pam

# Or perhaps:
# echo "Defaults env_keep += \"PATH\"" > /etc/sudoers.d/env
# Run `cat /etc/sudoers.d/vscode` for more info
# https://askubuntu.com/questions/161924
# https://stackoverflow.com/questions/66687881
# https://www.thegeekdiary.com/user-environment-variables-with-su-and-sudo-in-linux/
# https://superuser.com/questions/636283
# https://superuser.com/questions/232231
# https://unix.stackexchange.com/questions/8646
# https://unix.stackexchange.com/questions/292815
# https://askubuntu.com/questions/554970
# https://askubuntu.com/questions/1134889

apk add --no-cache \
    tidyhtml \
    github-cli \
    shellcheck \
    shfmt \
    editorconfig-checker \
    htop \
    ncdu \
    make \
    file \
    util-linux \
    diffutils \
    moreutils \
    bash-completion

# TODO: pandoc install fails for some reason
# TODO: prettier install fails for some reason

# -----------------------------------------------------------------------------

apk add --no-cache \
    libxml2 \
    libxml2-dev \
    libxslt \
    libxslt-dev \
    libtool \
    patch \
    autoconf \
    automake

# -----------------------------------------------------------------------------

apk add --no-cache \
    linux-headers \
    libffi-dev \
    openssl-dev \
    bzip2-dev \
    zlib-dev \
    readline-dev \
    sqlite-dev \
    bash

cat >>~/.bashrc <<EOF
PYENV_ROOT="/usr/local/pyenv"
export PYENV_ROOT

PATH="${PYENV_ROOT}/bin:${PYENV_ROOT}/shims:${PATH}"
export PATH

eval "$(pyenv virtualenv-init -)"
EOF

. ~/.bashrc

curl -fsSL https://pyenv.run | bash

py_install() {
    PY_MINOR="${1}"
    # Install the latest patch version
    PY_VERSION="$(
        pyenv install --list |
            grep "${PY_MINOR}" | sort -n | tail -n 1 | xargs
    )"
    pyenv install "${PY_MINOR}-dev"
    pyenv install "${PY_VERSION}"
    pyenv global "${PY_VERSION}"
}

py_install 3.6
py_install 3.7
py_install 3.8
py_install 3.9
py_install 3.10

pip3 install --upgrade pip

# apk add --no-cache \
#     python3 \
#     python3-dev \
#     py3-pip \
#     py3-cffi

pip3 install pipx

pipx ensurepath

pipx install poetry

# -----------------------------------------------------------------------------

apk add --no-cache npm
npm config set fund false --global
# TODO: Adding `--no-audit` prevents these commands from printing information
# about which packages are installed
echo "Installing Node packages..."
npm install --global --no-audit npm@latest
npm install --global --no-audit --prefer-dedupe \
    strip-ansi-cli \
    cspell \
    prettier \
    lintspaces-cli \
    dockerfilelint \
    markdownlint-cli \
    markdown-link-check \
    jscpd

# -----------------------------------------------------------------------------

# TODO: Can't seem to get remark-lint to work when I install it

# https://github.com/drewbourne/vscode-remark-lint
# https://github.com/remarkjs/remark-validate-links

# remark-cli \
# remark-lint \
# remark-preset-lint-markdown-style-guide \
# remark-stringify \

rm -rf /root/.cache
rm -rf /root/.config
rm -rf /root/.npm

# TODO: npm install github-actions-linter
# TODO: go install github.com/rhysd/actionlint/cmd/actionlint@latest