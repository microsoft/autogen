namespace Marketing.Agents;
public interface IWriter : IGrainWithStringKey
{
    Task<string> GetArticle();
}