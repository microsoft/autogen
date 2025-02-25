#!/bin/bash
OUT_DIR="./generated"

# Create output directory if it doesn't exist
mkdir -p $OUT_DIR

# Generate TypeScript code using ts-proto
protoc \
  --plugin="../../node_modules/.bin/protoc-gen-ts_proto" \
  --ts_proto_out="$OUT_DIR" \
  --ts_proto_opt="esModuleInterop=true,outputServices=grpc-js,env=node" \
  -I . \
  message.proto

# Make the generated code prettier
prettier --write "$OUT_DIR/**/*.ts"
