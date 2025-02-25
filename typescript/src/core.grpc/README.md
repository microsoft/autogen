# AutoGen TypeScript gRPC Implementation

This directory contains the TypeScript implementation of AutoGen's gRPC-based agent communication system.

## Prerequisites

Before using this module, ensure you have:

1. Protocol Buffers compiler (protoc) installed:
   ```bash
   # macOS (using Homebrew)
   brew install protobuf

   # Ubuntu/Debian
   sudo apt-get install protobuf-compiler

   # Windows
   # Download from https://github.com/protocolbuffers/protobuf/releases
   ```

2. Install prettier globally (needed for code formatting):
   ```bash
   npm install -g prettier
   ```

3. Required npm packages installed:
   ```bash
   npm install @grpc/grpc-js @grpc/proto-loader google-protobuf
   npm install --save-dev @types/google-protobuf grpc-tools ts-proto prettier
   ```

## Generating TypeScript Code from Protos

1. Make the generate script executable:
   ```bash
   chmod +x scripts/generate-protos.sh
   ```

2. Run the generate script:
   ```bash
   npm run generate
   ```

This will:
- Read proto definitions from `/protos/agent_worker.proto`
- Generate TypeScript code in `src/core.grpc/generated/`
- Format the generated code using prettier

## Running the tests

```
# from the repo /typescript directory
npm install
npm test
```

## Usage



