#!/usr/bin/env bash

set -e
set -x

cd website &&
    yarn install --frozen-lockfile --ignore-engines &&
    pydoc-markdown &&
    yarn build
