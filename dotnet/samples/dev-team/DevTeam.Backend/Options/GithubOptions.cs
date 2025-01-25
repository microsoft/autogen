// Copyright (c) Microsoft Corporation. All rights reserved.
// GithubOptions.cs

using System.ComponentModel.DataAnnotations;

namespace DevTeam.Options;
public class GithubOptions
{
    [Required]
    public required string AppKey { get; set; }
    [Required]
    public int AppId { get; set; }
    [Required]
    public long InstallationId { get; set; }
    [Required]
    public required string WebhookSecret { get; set; }
}
