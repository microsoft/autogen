# Getting Started with AutoGen gRPC

This sample demonstrates using AutoGen with gRPC communication between agents.

## Prerequisites

1. Install Protocol Buffer Compiler:

```bash
# macOS (using Homebrew)
brew install protobuf

# Ubuntu/Debian
sudo apt-get install protobuf-compiler

# Windows
# Download from https://github.com/protocolbuffers/protobuf/releases
```

2. Install prettier globally:
```bash
npm install -g prettier
```

## Setup

1. Install dependencies:
```bash
npm install
```

2. Generate TypeScript code from proto definitions:
```bash 
npm run generate
```

3. Run the sample:
```bash
npm start
```

## What's Happening

This sample shows how to:

1. Configure AutoGen to use gRPC communication
2. Define message types using Protocol Buffers
3. Create agents that communicate over gRPC:
   - Checker: Initiates counting and monitors updates
   - Modifier: Receives counts and increments them

The main differences from the basic sample are:

1. Uses `GrpcAgentRuntime` instead of `InProcessRuntime`
2. Messages are serialized using Protocol Buffers
3. Communication happens over gRPC instead of in-memory
