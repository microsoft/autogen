// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentExceptions.cs

namespace Microsoft.AutoGen.Contracts.Python;

public class CantHandleException : Exception
{
    public CantHandleException() : base("The handler cannot process the given message.") { }
    public CantHandleException(string message) : base(message) { }
    public CantHandleException(string message, Exception innerException) : base(message, innerException) { }
}

/// <summary>
/// Exception thrown when a message cannot be delivered.
/// </summary>
public class UndeliverableException : Exception
{
    public UndeliverableException() : base("The message cannot be delivered.") { }
    public UndeliverableException(string message) : base(message) { }
    public UndeliverableException(string message, Exception innerException) : base(message, innerException) { }
}

public class MessageDroppedException : Exception
{
    public MessageDroppedException() : base("The message was dropped.") { }
    public MessageDroppedException(string message) : base(message) { }
    public MessageDroppedException(string message, Exception innerException) : base(message, innerException) { }
}

public class NotAccessibleError : Exception
{
    public NotAccessibleError() : base("The requested value is not accessible.") { }
    public NotAccessibleError(string message) : base(message) { }
    public NotAccessibleError(string message, Exception innerException) : base(message, innerException) { }
}
