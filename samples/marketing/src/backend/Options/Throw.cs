namespace Marketing
{
    public static class Throw
    {
        public static void IfNullOrEmpty(string paramName, string value)
        {
            if (string.IsNullOrEmpty(value)) 
            { 
                throw new ArgumentNullException(paramName); 
            }
        }
    }
}
