namespace Microsoft.AutoGen.Extensions.AIModelClientHostingExtensions
{
    public static class AIClientOptions
    {
        public static AIClientOptions UseOpenAI(this AIClientOptions options)
        {
            options.ModelType = "OpenAI";
            return options;
        }

        public static AIClientOptions UseAzureOpenAI(this AIClientOptions options)
        {
            options.ModelType = "AzureOpenAI";
            return options;
        }

        public static AIClientOptions UseOpenAI(this AIClientOptions options, string modelType)
        {
            options.ModelType = modelType;
            return options;
        }

        public static AIClientOptions UseAzureOpenAI(this AIClientOptions options, string modelType)
        {
            options.ModelType = modelType;
            return options;
        }
    }
}