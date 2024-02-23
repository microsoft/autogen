![](/docs/images/github-sk-dev-team.png)

# How does the event flow look like?


### Hubber agent handles:
 ```
    NewAsk
        -> create PM issue
        -> create DevLead issue
        -> create a branch
```
```
    ReadmeGenerated
        -> post comment
```
```
    DevPlanGenerated
        -> post comment
```
```
    DevPlanFinished
        -> for each step, create Dev issue
```
```
    CodeGenerated
        -> post comment
```
```
    ReadmeFinished
        -> commit to branch
```
```
    SandboxRunFinished
        -> commit to branch
```

### AzureOps agent handles:
```
    ReadmeChainClosed
        -> store
        -> ReadmeStored
```
```
    CodeChainClosed
        -> store
        -> run in sandbox
```

### PM agent handles:
```
    ReadmeRequested
        -> ReadmeGenerated
```
```
    ChainClosed
        -> ReadmeFinished
```

### DevLead agent handles:
```
    DevPlanRequested
       -> DevPlanGenerated
```
```
    ChainClosed
        -> DevPlanFinished
```

### Dev handles:
```
    CodeGenerationRequested
        -> CodeGenerated
```
```
    ChainClosed
        -> CodeFinished
```