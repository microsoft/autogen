#!/bin/bash

# Load NVM
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# Install and use the desired Node.js version
nvm install --lts
nvm use --lts

# Install Yarn and start the website
npm install -g yarn
cd website
yarn install --frozen-lockfile --ignore-engines
pydoc-markdown
yarn start --port 3000 --host 0.0.0.0

# Keep the container running
tail -f /dev/null
