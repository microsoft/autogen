// Copyright (c) Microsoft Corporation. All rights reserved.
// Function_Call_With_Gemini.cs

#region Using
using AutoGen.Core;
using Google.Cloud.AIPlatform.V1;
#endregion Using
using FluentAssertions;

namespace AutoGen.Gemini.Sample;

#region MovieFunction
public partial class MovieFunction
{
    /// <summary>
    /// find movie titles currently playing in theaters based on any description, genre, title words, etc.
    /// </summary>
    /// <param name="location">The city and state, e.g. San Francisco, CA or a zip code e.g. 95616</param>
    /// <param name="description">Any kind of description including category or genre, title words, attributes, etc.</param>
    /// <returns></returns>
    [Function]
    public async Task<string> FindMovies(string location, string description)
    {
        // dummy implementation
        var movies = new List<string> { "Barbie", "Spiderman", "Batman" };
        var result = $"Movies playing in {location} based on {description} are: {string.Join(", ", movies)}";

        return result;
    }

    /// <summary>
    /// find theaters based on location and optionally movie title which is currently playing in theaters
    /// </summary>
    /// <param name="location">The city and state, e.g. San Francisco, CA or a zip code e.g. 95616</param>
    /// <param name="movie">Any movie title</param>
    [Function]
    public async Task<string> FindTheaters(string location, string movie)
    {
        // dummy implementation
        var theaters = new List<string> { "AMC", "Regal", "Cinemark" };
        var result = $"Theaters playing {movie} in {location} are: {string.Join(", ", theaters)}";

        return result;
    }

    /// <summary>
    /// Find the start times for movies playing in a specific theater
    /// </summary>
    /// <param name="location">The city and state, e.g. San Francisco, CA or a zip code e.g. 95616</param>
    /// <param name="movie">Any movie title</param>
    /// <param name="theater">Name of the theater</param>
    /// <param name="date">Date for requested showtime</param>
    /// <returns></returns>
    [Function]
    public async Task<string> GetShowtimes(string location, string movie, string theater, string date)
    {
        // dummy implementation
        var showtimes = new List<string> { "10:00 AM", "12:00 PM", "2:00 PM", "4:00 PM", "6:00 PM", "8:00 PM" };
        var result = $"Showtimes for {movie} at {theater} in {location} are: {string.Join(", ", showtimes)}";

        return result;
    }
}
#endregion MovieFunction

/// <summary>
/// Modified from https://ai.google.dev/gemini-api/docs/function-calling
/// </summary>
public partial class Function_Call_With_Gemini
{
    public static async Task RunAsync()
    {
        #region Create_Gemini_Agent
        var projectID = Environment.GetEnvironmentVariable("GCP_VERTEX_PROJECT_ID");

        if (projectID is null)
        {
            Console.WriteLine("Please set GCP_VERTEX_PROJECT_ID environment variable.");
            return;
        }

        var movieFunction = new MovieFunction();
        var functionMiddleware = new FunctionCallMiddleware(
            functions: [
                movieFunction.FindMoviesFunctionContract,
                movieFunction.FindTheatersFunctionContract,
                movieFunction.GetShowtimesFunctionContract
                ],
            functionMap: new Dictionary<string, Func<string, Task<string>>>
            {
                { movieFunction.FindMoviesFunctionContract.Name!, movieFunction.FindMoviesWrapper },
                { movieFunction.FindTheatersFunctionContract.Name!, movieFunction.FindTheatersWrapper },
                { movieFunction.GetShowtimesFunctionContract.Name!, movieFunction.GetShowtimesWrapper },
            });

        var geminiAgent = new GeminiChatAgent(
                name: "gemini",
                model: "gemini-1.5-flash-001",
                location: "us-central1",
                project: projectID,
                systemMessage: "You are a helpful AI assistant",
                toolConfig: new ToolConfig()
                {
                    FunctionCallingConfig = new FunctionCallingConfig()
                    {
                        Mode = FunctionCallingConfig.Types.Mode.Auto,
                    }
                })
            .RegisterMessageConnector()
            .RegisterPrintMessage()
            .RegisterStreamingMiddleware(functionMiddleware);
        #endregion Create_Gemini_Agent

        #region Single_turn
        var question = new TextMessage(Role.User, "What movies are showing in North Seattle tonight?");
        var functionCallReply = await geminiAgent.SendAsync(question);
        #endregion Single_turn

        #region Single_turn_verify_reply
        functionCallReply.Should().BeOfType<ToolCallAggregateMessage>();
        #endregion Single_turn_verify_reply

        #region Multi_turn
        var finalReply = await geminiAgent.SendAsync(chatHistory: [question, functionCallReply]);
        #endregion Multi_turn

        #region Multi_turn_verify_reply
        finalReply.Should().BeOfType<TextMessage>();
        #endregion Multi_turn_verify_reply
    }
}
