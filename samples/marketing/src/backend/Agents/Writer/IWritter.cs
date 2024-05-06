namespace Marketing.Agents;
public interface IWriter : IGrainWithStringKey
{
    Task<String> GetArticle();
}