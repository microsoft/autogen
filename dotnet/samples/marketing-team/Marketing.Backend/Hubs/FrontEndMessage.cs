// Copyright (c) Microsoft Corporation. All rights reserved.
// FrontEndMessage.cs

namespace Marketing.Backend.Hubs;

public class FrontEndMessage
{
    public required string UserId { get; set; }
    public required string Message { get; set; }
    public required string Agent { get; set; }
}
