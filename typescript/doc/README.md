# Building the AutoGen TypeScript Documentation

This directory contains the documentation for the AutoGen TypeScript implementation.

## Prerequisites

- Node.js 18 or later
- npm 8 or later
- TypeDoc (`npm install -g typedoc`)

## Building Documentation

1. Install dependencies:
```bash
npm install
```

2. Generate API documentation:
```bash
npm run docs
```

The documentation will be generated in the `_site` directory.

## Documentation Structure

- `index.md` - Main documentation and getting started guide
- `core/` - Documentation for the core module
  - `agents.md` - Agent system documentation
  - `runtime.md` - Runtime system documentation
  - `subscriptions.md` - Subscription system documentation

## Contributing

When contributing to the documentation:

1. Use TypeScript-specific examples
2. Include type information in code samples
3. Follow the TypeScript documentation style guide
4. Test all code samples
