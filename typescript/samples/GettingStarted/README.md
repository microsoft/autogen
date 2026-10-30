# AutoGen TypeScript Getting Started Sample

This sample demonstrates a simple multi-agent interaction using the AutoGen TypeScript framework. It shows how to create agents that can communicate with each other through messages and coordinated actions.

## Overview

The sample implements a counting sequence where:
1. A "Modifier" agent receives a number and decrements it
2. A "Checker" agent verifies the number and either:
   - Continues the sequence if the number is > 1
   - Stops the program if the number reaches 1

## Agents

### Modifier Agent
- Receives a `CountMessage` containing a number
- Decrements the number using a modifier function
- Publishes a `CountUpdate` with the new value

### Checker Agent
- Receives the `CountUpdate` from the Modifier
- Checks if the number meets the termination condition
- Either continues the sequence or shuts down the application

## Running the Sample

1. Make sure you have Node.js and npm installed

2. Install dependencies:
```bash
npm install
```

3. Run the sample:
```bash
npm start
```

## Expected Output
You should see output similar to this:

```
Counting complete!
```



