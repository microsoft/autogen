#!/bin/bash

cd website
yarn install --frozen-lockfile --ignore-engines
pydoc-markdown
yarn start --host 0.0.0.0 --port 3000
