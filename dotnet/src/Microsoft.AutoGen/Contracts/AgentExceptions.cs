// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentExceptions.cs

namespace Microsoft.AutoGen.Contracts;

/// <summary>
/// Exception thrown when a handler cannot process the given message.
/// </summary>
public class CantHandleException : Exception
{
    /// <summary>
    /// Initializes a new instance of the <see cref="CantHandleException"/> class.
    /// </summary>
    public CantHandleException() : base("The handler cannot process the given message.") { }

    /// <summary>
    /// Initializes a new instance of the <see cref="CantHandleException"/> class with a custom error message.
    /// </summary>
    /// <param name="message">The custom error message.</param>
    public CantHandleException(string message) : base(message) { }

    /// <summary>
    /// Initializes a new instance of the <see cref="CantHandleException"/> class with a custom error message and an inner exception.
    /// </summary>
    /// <param name="message">The custom error message.</param>
    /// <param name="innerException">The inner exception that caused this error.</param>
    public CantHandleException(string message, Exception innerException) : base(message, innerException) { }
}

/// <summary>
/// Exception thrown when a message cannot be delivered.
/// </summary>
public class UndeliverableException : Exception
{
    /// <summary>
    /// Initializes a new instance of the <see cref="UndeliverableException"/> class.
    /// </summary>
    public UndeliverableException() : base("The message cannot be delivered.") { }

    /// <summary>
    /// Initializes a new instance of the <see cref="UndeliverableException"/> class with a custom error message.
    /// </summary>
    /// <param name="message">The custom error message.</param>
    public UndeliverableException(string message) : base(message) { }

    /// <summary>
    /// Initializes a new instance of the <see cref="UndeliverableException"/> class with a custom error message and an inner exception.
    /// </summary>
    /// <param name="message">The custom error message.</param>
    /// <param name="innerException">The inner exception that caused this error.</param>
    public UndeliverableException(string message, Exception innerException) : base(message, innerException) { }
}

/// <summary>
/// Exception thrown when a message is dropped.
/// </summary>
public class MessageDroppedException : Exception
{
    /// <summary>
    /// Initializes a new instance of the <see cref="MessageDroppedException"/> class.
    /// </summary>
    public MessageDroppedException() : base("The message was dropped.") { }

    /// <summary>
    /// Initializes a new instance of the <see cref="MessageDroppedException"/> class with a custom error message.
    /// </summary>
    /// <param name="message">The custom error message.</param>
    public MessageDroppedException(string message) : base(message) { }

    /// <summary>
    /// Initializes a new instance of the <see cref="MessageDroppedException"/> class with a custom error message and an inner exception.
    /// </summary>
    /// <param name="message">The custom error message.</param>
    /// <param name="innerException">The inner exception that caused this error.</param>
    public MessageDroppedException(string message, Exception innerException) : base(message, innerException) { }
}

/// <summary>
/// Exception thrown when an attempt is made to access an unavailable value, such as a remote resource.
/// </summary>
public class NotAccessibleError : Exception
{
    /// <summary>
    /// Initializes a new instance of the <see cref="NotAccessibleError"/> class.
    /// </summary>
    public NotAccessibleError() : base("The requested value is not accessible.") { }

    /// <summary>
    /// Initializes a new instance of the <see cref="NotAccessibleError"/> class with a custom error message.
    /// </summary>
    /// <param name="message">The custom error message.</param>
    public NotAccessibleError(string message) : base(message) { }

    /// <summary>
    /// Initializes a new instance of the <see cref="NotAccessibleError"/> class with a custom error message and an inner exception.
    /// </summary>
    /// <param name="message">The custom error message.</param>
    /// <param name="innerException">The inner exception that caused this error.</param>
    public NotAccessibleError(string message, Exception innerException) : base(message, innerException) { }
}
