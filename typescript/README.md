# AutoGen TypeScript Implementation

This is the TypeScript implementation of the AutoGen framework.

## Prerequisites

- Node.js 18 or later
- npm 8 or later

## Setup

Install dependencies:

```bash
npm install
```

## Building

The project uses TypeScript and can be built using:

```bash
npm run build
```

## Testing

Run all tests:

```bash
npm test
```

Run specific test file(s):
```bash
npm test test/core/InProcessRuntime.test.ts
```

Run tests matching a pattern:
```bash
npm test -- -t "should not deliver to self"
```

Run tests in watch mode during development:

```bash
npm run test:watch
```

## Project Structure

- `/src` - Source code
  - `/contracts` - Interface definitions
  - `/core` - Core implementation
- `/test` - Test files
  - `/core` - Core tests

## Development Notes

- The project uses Jest for testing
- TypeScript decorators are enabled and used for subscriptions
- Tests require `reflect-metadata` for decorator support
