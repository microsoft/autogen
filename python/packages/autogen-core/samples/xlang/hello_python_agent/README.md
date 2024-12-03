# Python and dotnet agents interoperability sample

This sample demonstrates how to create a Python agent that interacts with a .NET agent.
To run the sample, check out the autogen repository.
Then do the following:

1. Navigate to autogen/dotnet/samples/Hello/Hello.AppHost
2. Run `dotnet run` to start the .NET Aspire app host, which runs three projects:
    - Backend (the .NET Agent Runtime)
    - HelloAgent (the .NET Agent)
    - this Python agent - hello_python_agent.py
3. The AppHost will start the Aspire dashboard on [https://localhost:15887](https://localhost:15887).

The Python agent will interact with the .NET agent by sending a message to the .NET runtime, which will relay the message to the .NET agent.
