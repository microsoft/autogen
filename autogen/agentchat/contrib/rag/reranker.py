from typing import List, Optional, Protocol, Tuple, Union, runtime_checkable

from .datamodel import Query
from .utils import lazy_import, timer


@runtime_checkable
class Reranker(Protocol):
    """
    Abstract class for reranker. A reranker is responsible for reranking documents based on the query.
    """

    def rerank(
        self,
        query: Query,
        docs: Optional[List[str]] = None,
        return_docs: bool = False,
    ) -> List[Tuple[str, float]]:
        """
        Rerank documents based on the query.

        Args:
            query: Query | The query.
            docs: Optional[List[str]] | The list of documents. Default is None.
            return_docs: bool | Whether to return the documents. Default is False.

        Returns:
            List[Tuple[str, float]] | The reranked documents with scores.
        """
        ...


class TfidfReranker:
    """
    A simple TFIDF reranker.
    """

    def __init__(self) -> None:
        TfidfVectorizer = lazy_import("sklearn.feature_extraction.text", "TfidfVectorizer")
        if not TfidfVectorizer:
            raise ImportError("Please install sklearn to use TfidfReranker.")
        self.vectorizer = TfidfVectorizer()
        self.docs = None

    def vectorize(self, docs: List[str]) -> None:
        """
        Vectorize the documents.

        Args:
            docs: List[str] | The list of documents.

        Returns:
            None
        """
        self.docs = docs
        self.corpus_tfidf = self.vectorizer.fit_transform(docs)

    @timer
    def rerank(
        self,
        query: Query,
        docs: Optional[List[str]] = None,
        return_docs: bool = False,
        return_scores: bool = False,
    ) -> List[Union[int, Tuple[Union[int, str], float]]]:
        """
        Rerank documents based on the query.

        Args:
            query: Query | The query.
            docs: Optional[List[str]] | The list of documents. Default is None.
            return_docs: bool | Whether to return the documents. Default is False.
            return_scores: bool | Whether to return the scores. Default is False.

        Returns:
            List[Union[int, Tuple[Union[int, str], float]]] | The reranked documents or the reranked documents with scores.
        """
        if docs and self.docs != docs:
            self.vectorize(docs)
        if not docs and not self.docs:
            raise ValueError("Please provide documents to fit the reranker.")
        query_tfidf = self.vectorizer.transform([query.text])
        scores = self.corpus_tfidf.dot(query_tfidf.T).toarray().flatten()
        ranked_docs = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        if return_scores:
            if return_docs:
                return [(self.docs[doc[0]], doc[1]) for doc in ranked_docs[: query.k]]
            else:
                return ranked_docs[: query.k]
        else:
            if return_docs:
                return [self.docs[doc[0]] for doc in ranked_docs[: query.k]]
            else:
                return [doc[0] for doc in ranked_docs[: query.k]]


class RerankerFactory:
    """
    Factory class for creating rerankers.
    """

    PREDEFINED_RERANKERS = frozenset({"tfidf"})

    @staticmethod
    def create_reranker(reranker_name: str, **kwargs) -> Reranker:
        """
        Create a reranker.

        Args:
            reranker_name: str | The name of the reranker.
            **kwargs: dict | Additional keyword arguments.

        Returns:
            Reranker | The reranker.
        """
        if reranker_name == "tfidf":
            return TfidfReranker(**kwargs)
        else:
            raise ValueError(
                f"Reranker {reranker_name} is not supported. Valid rerankers are {RerankerFactory.PREDEFINED_RERANKERS}."
            )
