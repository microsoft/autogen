// Copyright (c) Microsoft Corporation. All rights reserved.
// Model.cs

using System;
using System.Text.Json.Serialization;

namespace AutoGen.Mistral;

public class Model
{
    /// <summary>
    /// Initializes a new instance of the <see cref="Model" /> class.
    /// </summary>
    /// <param name="id">id (required).</param>
    /// <param name="varObject">varObject (required).</param>
    /// <param name="created">created (required).</param>
    /// <param name="ownedBy">ownedBy (required).</param>
    public Model(string? id = default(string), string? varObject = default(string), int created = default(int), string? ownedBy = default(string))
    {
        // to ensure "id" is required (not null)
        if (id == null)
        {
            throw new ArgumentNullException("id is a required property for Model and cannot be null");
        }
        this.Id = id;
        // to ensure "varObject" is required (not null)
        if (varObject == null)
        {
            throw new ArgumentNullException("varObject is a required property for Model and cannot be null");
        }
        this.VarObject = varObject;
        this.Created = created;
        // to ensure "ownedBy" is required (not null)
        if (ownedBy == null)
        {
            throw new ArgumentNullException("ownedBy is a required property for Model and cannot be null");
        }
        this.OwnedBy = ownedBy;
    }

    /// <summary>
    /// Gets or Sets Id
    /// </summary>
    [JsonPropertyName("id")]
    public string Id { get; set; }

    /// <summary>
    /// Gets or Sets VarObject
    /// </summary>
    [JsonPropertyName("object")]
    public string VarObject { get; set; }

    /// <summary>
    /// Gets or Sets Created
    /// </summary>
    [JsonPropertyName("created")]
    public int Created { get; set; }

    /// <summary>
    /// Gets or Sets OwnedBy
    /// </summary>
    [JsonPropertyName("owned_by")]
    public string OwnedBy { get; set; }
}
