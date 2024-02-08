from autogen.agentchat.contrib.rag.encoder import Encoder, SentenceTransformerEmbeddingFunction, EmbeddingFunction


def test_sentence_transformer_embedding_function():
    embedding_function = SentenceTransformerEmbeddingFunction()
    assert callable(embedding_function)
    assert hasattr(embedding_function, "__call__")
    assert isinstance(embedding_function, EmbeddingFunction)
    embed1 = embedding_function("hello world")
    embed2 = embedding_function(["hello world", "goodbye world"])
    assert isinstance(embed1, list)
    assert isinstance(embed2, list)
    assert isinstance(embed1[0], list)
    assert isinstance(embed2[0], list)
    assert isinstance(embed1[0][0], float)
    assert isinstance(embed2[0][0], float)
    assert len(embed1) == 1
    assert len(embed2) == 2
    assert len(embed1[0]) == embedding_function.dimensions
    assert len(embed2[0]) == embedding_function.dimensions


if __name__ == "__main__":
    test_sentence_transformer_embedding_function()
    import chromadb.utils.embedding_functions as ef

    eff = ef.SentenceTransformerEmbeddingFunction("all-MiniLM-L6-v2")
    print(isinstance(eff, EmbeddingFunction))
    print(type(eff))
    r = eff(["hello world"])
    print(len(r))
    print(type(r))
    print(len(r[0]))
