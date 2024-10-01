import os
import re
import urllib.parse
from typing import Callable, List, Optional, Union

import numpy as np
from sentence_transformers import SentenceTransformer

from .base import Document, ItemID, QueryResults, VectorDB
from .utils import get_logger

try:
    import pgvector
    from pgvector.psycopg import register_vector
except ImportError:
    raise ImportError("Please install pgvector: `pip install pgvector`")

try:
    import psycopg
except ImportError:
    raise ImportError("Please install pgvector: `pip install psycopg`")

PGVECTOR_MAX_BATCH_SIZE = os.environ.get("PGVECTOR_MAX_BATCH_SIZE", 40000)
logger = get_logger(__name__)


class Collection:
    """
    A Collection object for PGVector.

    Attributes:
        client: The PGVector client.
        collection_name (str): The name of the collection. Default is "documents".
        embedding_function (Callable): The embedding function used to generate the vector representation.
            Default is None. SentenceTransformer("all-MiniLM-L6-v2").encode will be used when None.
            Models can be chosen from:
            https://huggingface.co/models?library=sentence-transformers
        metadata (Optional[dict]): The metadata of the collection.
        get_or_create (Optional): The flag indicating whether to get or create the collection.
    """

    def __init__(
        self,
        client=None,
        collection_name: str = "autogen-docs",
        embedding_function: Callable = None,
        metadata=None,
        get_or_create=None,
    ):
        """
        Initialize the Collection object.

        Args:
            client: The PostgreSQL client.
            collection_name: The name of the collection. Default is "documents".
            embedding_function: The embedding function used to generate the vector representation.
            metadata: The metadata of the collection.
            get_or_create: The flag indicating whether to get or create the collection.
        Returns:
            None
        """
        self.client = client
        self.name = self.set_collection_name(collection_name)
        self.require_embeddings_or_documents = False
        self.ids = []
        if embedding_function:
            self.embedding_function = embedding_function
        else:
            self.embedding_function = SentenceTransformer("all-MiniLM-L6-v2").encode
        self.metadata = metadata if metadata else {"hnsw:space": "ip", "hnsw:construction_ef": 32, "hnsw:M": 16}
        self.documents = ""
        self.get_or_create = get_or_create
        # This will get the model dimension size by computing the embeddings dimensions
        sentences = [
            "The weather is lovely today in paradise.",
        ]
        embeddings = self.embedding_function(sentences)
        self.dimension = len(embeddings[0])

    def set_collection_name(self, collection_name) -> str:
        name = re.sub("-", "_", collection_name)
        self.name = name
        return self.name

    def add(self, ids: List[ItemID], documents: List, embeddings: List = None, metadatas: List = None) -> None:
        """
        Add documents to the collection.

        Args:
            ids (List[ItemID]): A list of document IDs.
            embeddings (List): A list of document embeddings. Optional
            metadatas (List): A list of document metadatas. Optional
            documents (List): A list of documents.

        Returns:
            None
        """
        cursor = self.client.cursor()
        sql_values = []
        if embeddings is not None and metadatas is not None:
            for doc_id, embedding, metadata, document in zip(ids, embeddings, metadatas, documents):
                metadata = re.sub("'", '"', str(metadata))
                sql_values.append((doc_id, embedding, metadata, document))
            sql_string = (
                f"INSERT INTO {self.name} (id, embedding, metadatas, documents)\n" f"VALUES (%s, %s, %s, %s);\n"
            )
        elif embeddings is not None:
            for doc_id, embedding, document in zip(ids, embeddings, documents):
                sql_values.append((doc_id, embedding, document))
            sql_string = f"INSERT INTO {self.name} (id, embedding, documents) " f"VALUES (%s, %s, %s);\n"
        elif metadatas is not None:
            for doc_id, metadata, document in zip(ids, metadatas, documents):
                metadata = re.sub("'", '"', str(metadata))
                embedding = self.embedding_function(document)
                sql_values.append((doc_id, metadata, embedding, document))
            sql_string = (
                f"INSERT INTO {self.name} (id, metadatas, embedding, documents)\n" f"VALUES (%s, %s, %s, %s);\n"
            )
        else:
            for doc_id, document in zip(ids, documents):
                embedding = self.embedding_function(document)
                sql_values.append((doc_id, document, embedding))
            sql_string = f"INSERT INTO {self.name} (id, documents, embedding)\n" f"VALUES (%s, %s, %s);\n"
        logger.debug(f"Add SQL String:\n{sql_string}\n{sql_values}")
        cursor.executemany(sql_string, sql_values)
        cursor.close()

    def upsert(self, ids: List[ItemID], documents: List, embeddings: List = None, metadatas: List = None) -> None:
        """
        Upsert documents into the collection.

        Args:
            ids (List[ItemID]): A list of document IDs.
            documents (List): A list of documents.
            embeddings (List): A list of document embeddings.
            metadatas (List): A list of document metadatas.

        Returns:
            None
        """
        cursor = self.client.cursor()
        sql_values = []
        if embeddings is not None and metadatas is not None:
            for doc_id, embedding, metadata, document in zip(ids, embeddings, metadatas, documents):
                metadata = re.sub("'", '"', str(metadata))
                sql_values.append((doc_id, embedding, metadata, document, embedding, metadata, document))
            sql_string = (
                f"INSERT INTO {self.name} (id, embedding, metadatas, documents)\n"
                f"VALUES (%s, %s, %s, %s)\n"
                f"ON CONFLICT (id)\n"
                f"DO UPDATE SET embedding = %s,\n"
                f"metadatas = %s, documents = %s;\n"
            )
        elif embeddings is not None:
            for doc_id, embedding, document in zip(ids, embeddings, documents):
                sql_values.append((doc_id, embedding, document, embedding, document))
            sql_string = (
                f"INSERT INTO {self.name} (id, embedding, documents) "
                f"VALUES (%s, %s, %s) ON CONFLICT (id)\n"
                f"DO UPDATE SET embedding = %s, documents = %s;\n"
            )
        elif metadatas is not None:
            for doc_id, metadata, document in zip(ids, metadatas, documents):
                metadata = re.sub("'", '"', str(metadata))
                embedding = self.embedding_function(document)
                sql_values.append((doc_id, metadata, embedding, document, metadata, document, embedding))
            sql_string = (
                f"INSERT INTO {self.name} (id, metadatas, embedding, documents)\n"
                f"VALUES (%s, %s, %s, %s)\n"
                f"ON CONFLICT (id)\n"
                f"DO UPDATE SET metadatas = %s, documents = %s, embedding = %s;\n"
            )
        else:
            for doc_id, document in zip(ids, documents):
                embedding = self.embedding_function(document)
                sql_values.append((doc_id, document, embedding, document))
            sql_string = (
                f"INSERT INTO {self.name} (id, documents, embedding)\n"
                f"VALUES (%s, %s, %s)\n"
                f"ON CONFLICT (id)\n"
                f"DO UPDATE SET documents = %s;\n"
            )
        logger.debug(f"Upsert SQL String:\n{sql_string}\n{sql_values}")
        cursor.executemany(sql_string, sql_values)
        cursor.close()

    def count(self) -> int:
        """
        Get the total number of documents in the collection.

        Returns:
            int: The total number of documents.
        """
        cursor = self.client.cursor()
        query = f"SELECT COUNT(*) FROM {self.name}"
        cursor.execute(query)
        total = cursor.fetchone()[0]
        cursor.close()
        try:
            total = int(total)
        except (TypeError, ValueError):
            total = None
        return total

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the PostgreSQL database.

        Args:
            table_name (str): The name of the table to check.

        Returns:
            bool: True if the table exists, False otherwise.
        """

        cursor = self.client.cursor()
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = %s
            )
            """,
            (table_name,),
        )
        exists = cursor.fetchone()[0]
        return exists

    def get(
        self,
        ids: Optional[str] = None,
        include: Optional[str] = None,
        where: Optional[str] = None,
        limit: Optional[Union[int, str]] = None,
        offset: Optional[Union[int, str]] = None,
    ) -> List[Document]:
        """
        Retrieve documents from the collection.

        Args:
            ids (Optional[List]): A list of document IDs.
            include (Optional): The fields to include.
            where (Optional): Additional filtering criteria.
            limit (Optional): The maximum number of documents to retrieve.
            offset (Optional): The offset for pagination.

        Returns:
            List: The retrieved documents.
        """
        cursor = self.client.cursor()

        # Initialize variables for query components
        select_clause = "SELECT id, metadatas, documents, embedding"
        from_clause = f"FROM {self.name}"
        where_clause = ""
        limit_clause = ""
        offset_clause = ""

        # Handle include clause
        if include:
            select_clause = f"SELECT id, {', '.join(include)}, embedding"

        # Handle where clause
        if ids:
            where_clause = f"WHERE id IN ({', '.join(['%s' for _ in ids])})"
        elif where:
            where_clause = f"WHERE {where}"

        # Handle limit and offset clauses
        if limit:
            limit_clause = "LIMIT %s"
        if offset:
            offset_clause = "OFFSET %s"

        # Construct the full query
        query = f"{select_clause} {from_clause} {where_clause} {limit_clause} {offset_clause}"
        retrieved_documents = []
        try:
            # Execute the query with the appropriate values
            if ids is not None:
                cursor.execute(query, ids)
            else:
                query_params = []
                if limit:
                    query_params.append(limit)
                if offset:
                    query_params.append(offset)
                cursor.execute(query, query_params)

            retrieval = cursor.fetchall()
            for retrieved_document in retrieval:
                retrieved_documents.append(
                    Document(
                        id=retrieved_document[0].strip(),
                        metadata=retrieved_document[1],
                        content=retrieved_document[2],
                        embedding=retrieved_document[3],
                    )
                )
        except (psycopg.errors.UndefinedTable, psycopg.errors.UndefinedColumn) as e:
            logger.info(f"Error executing select on non-existent table: {self.name}. Creating it instead. Error: {e}")
            self.create_collection(collection_name=self.name, dimension=self.dimension)
            logger.info(f"Created table {self.name}")

        cursor.close()
        return retrieved_documents

    def update(self, ids: List, embeddings: List, metadatas: List, documents: List) -> None:
        """
        Update documents in the collection.

        Args:
            ids (List): A list of document IDs.
            embeddings (List): A list of document embeddings.
            metadatas (List): A list of document metadatas.
            documents (List): A list of documents.

        Returns:
            None
        """
        cursor = self.client.cursor()
        sql_values = []
        for doc_id, embedding, metadata, document in zip(ids, embeddings, metadatas, documents):
            sql_values.append((doc_id, embedding, metadata, document, doc_id, embedding, metadata, document))
        sql_string = (
            f"INSERT INTO {self.name} (id, embedding, metadata, document) "
            f"VALUES (%s, %s, %s, %s) "
            f"ON CONFLICT (id) "
            f"DO UPDATE SET id = %s, embedding = %s, "
            f"metadata = %s, document = %s;\n"
        )
        logger.debug(f"Upsert SQL String:\n{sql_string}\n")
        cursor.executemany(sql_string, sql_values)
        cursor.close()

    @staticmethod
    def euclidean_distance(arr1: List[float], arr2: List[float]) -> float:
        """
        Calculate the Euclidean distance between two vectors.

        Parameters:
        - arr1 (List[float]): The first vector.
        - arr2 (List[float]): The second vector.

        Returns:
        - float: The Euclidean distance between arr1 and arr2.
        """
        dist = np.linalg.norm(arr1 - arr2)
        return dist

    @staticmethod
    def cosine_distance(arr1: List[float], arr2: List[float]) -> float:
        """
        Calculate the cosine distance between two vectors.

        Parameters:
        - arr1 (List[float]): The first vector.
        - arr2 (List[float]): The second vector.

        Returns:
        - float: The cosine distance between arr1 and arr2.
        """
        dist = np.dot(arr1, arr2) / (np.linalg.norm(arr1) * np.linalg.norm(arr2))
        return dist

    @staticmethod
    def inner_product_distance(arr1: List[float], arr2: List[float]) -> float:
        """
        Calculate the Euclidean distance between two vectors.

        Parameters:
        - arr1 (List[float]): The first vector.
        - arr2 (List[float]): The second vector.

        Returns:
        - float: The Euclidean distance between arr1 and arr2.
        """
        dist = np.linalg.norm(arr1 - arr2)
        return dist

    def query(
        self,
        query_texts: List[str],
        collection_name: Optional[str] = None,
        n_results: Optional[int] = 10,
        distance_type: Optional[str] = "euclidean",
        distance_threshold: Optional[float] = -1,
        include_embedding: Optional[bool] = False,
    ) -> QueryResults:
        """
        Query documents in the collection.

        Args:
            query_texts (List[str]): A list of query texts.
            collection_name (Optional[str]): The name of the collection.
            n_results (int): The maximum number of results to return.
            distance_type (Optional[str]): Distance search type - euclidean or cosine
            distance_threshold (Optional[float]): Distance threshold to limit searches
            include_embedding (Optional[bool]): Include embedding values in QueryResults
        Returns:
            QueryResults: The query results.
        """
        if collection_name:
            self.name = collection_name

        clause = "ORDER BY"
        if distance_threshold == -1:
            distance_threshold = ""
            clause = "ORDER BY"
        elif distance_threshold > 0:
            distance_threshold = f"< {distance_threshold}"
            clause = "WHERE"

        cursor = self.client.cursor()
        results = []
        for query_text in query_texts:
            vector = self.embedding_function(query_text)

            if distance_type.lower() == "cosine":
                index_function = "<=>"
            elif distance_type.lower() == "euclidean":
                index_function = "<->"
            elif distance_type.lower() == "inner-product":
                index_function = "<#>"
            else:
                index_function = "<->"
            query = (
                f"SELECT id, documents, embedding, metadatas "
                f"FROM {self.name} "
                f"{clause} embedding {index_function} '{str(vector)}' {distance_threshold} "
                f"LIMIT {n_results}"
            )
            cursor.execute(query)
            result = []
            for row in cursor.fetchall():
                fetched_document = Document(id=row[0].strip(), content=row[1], embedding=row[2], metadata=row[3])
                fetched_document_array = self.convert_string_to_array(array_string=fetched_document.get("embedding"))
                if distance_type.lower() == "cosine":
                    distance = self.cosine_distance(fetched_document_array, vector)
                elif distance_type.lower() == "euclidean":
                    distance = self.euclidean_distance(fetched_document_array, vector)
                elif distance_type.lower() == "inner-product":
                    distance = self.inner_product_distance(fetched_document_array, vector)
                else:
                    distance = self.euclidean_distance(fetched_document_array, vector)
                if not include_embedding:
                    fetched_document = Document(id=row[0].strip(), content=row[1], metadata=row[3])
                result.append((fetched_document, distance))
            results.append(result)
        cursor.close()
        logger.debug(f"Query Results: {results}")
        return results

    @staticmethod
    def convert_string_to_array(array_string: str) -> List[float]:
        """
        Convert a string representation of an array to a list of floats.

        Parameters:
        - array_string (str): The string representation of the array.

        Returns:
        - list: A list of floats parsed from the input string. If the input is
          not a string, it returns the input itself.
        """
        if not isinstance(array_string, str):
            return array_string
        array_string = array_string.strip("[]")
        array = [float(num) for num in array_string.split()]
        return array

    def modify(self, metadata, collection_name: Optional[str] = None) -> None:
        """
        Modify metadata for the collection.

        Args:
            collection_name: The name of the collection.
            metadata: The new metadata.

        Returns:
            None
        """
        if collection_name:
            self.name = collection_name
        cursor = self.client.cursor()
        cursor.execute(
            "UPDATE collections" "SET metadata = '%s'" "WHERE collection_name = '%s';", (metadata, self.name)
        )
        cursor.close()

    def delete(self, ids: List[ItemID], collection_name: Optional[str] = None) -> None:
        """
        Delete documents from the collection.

        Args:
            ids (List[ItemID]): A list of document IDs to delete.
            collection_name (str): The name of the collection to delete.

        Returns:
            None
        """
        if collection_name:
            self.name = collection_name
        cursor = self.client.cursor()
        id_placeholders = ", ".join(["%s" for _ in ids])
        cursor.execute(f"DELETE FROM {self.name} WHERE id IN ({id_placeholders});", ids)
        cursor.close()

    def delete_collection(self, collection_name: Optional[str] = None) -> None:
        """
        Delete the entire collection.

        Args:
            collection_name (Optional[str]): The name of the collection to delete.

        Returns:
            None
        """
        if collection_name:
            self.name = collection_name
        cursor = self.client.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS {self.name}")
        cursor.close()

    def create_collection(
        self, collection_name: Optional[str] = None, dimension: Optional[Union[str, int]] = None
    ) -> None:
        """
        Create a new collection.

        Args:
            collection_name (Optional[str]): The name of the new collection.
            dimension (Optional[Union[str, int]]): The dimension size of the sentence embedding model

        Returns:
            None
        """
        if collection_name:
            self.name = collection_name

        if dimension:
            self.dimension = dimension
        elif self.dimension is None:
            self.dimension = 384

        cursor = self.client.cursor()
        cursor.execute(
            f"CREATE TABLE {self.name} ("
            f"documents text, id CHAR(8) PRIMARY KEY, metadatas JSONB, embedding vector({self.dimension}));"
            f"CREATE INDEX "
            f'ON {self.name} USING hnsw (embedding vector_l2_ops) WITH (m = {self.metadata["hnsw:M"]}, '
            f'ef_construction = {self.metadata["hnsw:construction_ef"]});'
            f"CREATE INDEX "
            f'ON {self.name} USING hnsw (embedding vector_cosine_ops) WITH (m = {self.metadata["hnsw:M"]}, '
            f'ef_construction = {self.metadata["hnsw:construction_ef"]});'
            f"CREATE INDEX "
            f'ON {self.name} USING hnsw (embedding vector_ip_ops) WITH (m = {self.metadata["hnsw:M"]}, '
            f'ef_construction = {self.metadata["hnsw:construction_ef"]});'
        )
        cursor.close()


class PGVectorDB(VectorDB):
    """
    A vector database that uses PGVector as the backend.
    """

    def __init__(
        self,
        *,
        conn: Optional[psycopg.Connection] = None,
        connection_string: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[Union[int, str]] = None,
        dbname: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        connect_timeout: Optional[int] = 10,
        embedding_function: Callable = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Initialize the vector database.

        Note: connection_string or host + port + dbname must be specified

        Args:
            conn: psycopg.Connection | A customer connection object to connect to the database.
                A connection object may include additional key/values:
                https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING
            connection_string: "postgresql://username:password@hostname:port/database" | The PGVector connection string. Default is None.
            host: str | The host to connect to. Default is None.
            port: int | The port to connect to. Default is None.
            dbname: str | The database name to connect to. Default is None.
            username: str | The database username to use. Default is None.
            password: str | The database user password to use. Default is None.
            connect_timeout: int | The timeout to set for the connection. Default is 10.
            embedding_function: Callable | The embedding function used to generate the vector representation.
                Default is None. SentenceTransformer("all-MiniLM-L6-v2").encode will be used when None.
                Models can be chosen from:
                https://huggingface.co/models?library=sentence-transformers
            metadata: dict | The metadata of the vector database. Default is None. If None, it will use this
                setting: {"hnsw:space": "ip", "hnsw:construction_ef": 30, "hnsw:M": 16}. Creates Index on table
                using hnsw (embedding vector_l2_ops) WITH (m = hnsw:M) ef_construction = "hnsw:construction_ef".
                For more info: https://github.com/pgvector/pgvector?tab=readme-ov-file#hnsw
        Returns:
            None
        """
        self.client = self.establish_connection(
            conn=conn,
            connection_string=connection_string,
            host=host,
            port=port,
            dbname=dbname,
            username=username,
            password=password,
            connect_timeout=connect_timeout,
        )
        if embedding_function:
            self.embedding_function = embedding_function
        else:
            self.embedding_function = lambda s: SentenceTransformer("all-MiniLM-L6-v2").encode(s).tolist()
        self.metadata = metadata
        register_vector(self.client)
        self.active_collection = None

    def establish_connection(
        self,
        conn: Optional[psycopg.Connection] = None,
        connection_string: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[Union[int, str]] = None,
        dbname: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        connect_timeout: Optional[int] = 10,
    ) -> psycopg.Connection:
        """
        Establishes a connection to a PostgreSQL database using psycopg.

        Args:
            conn: An existing psycopg connection object. If provided, this connection will be used.
            connection_string: A string containing the connection information. If provided, a new connection will be established using this string.
            host: The hostname of the PostgreSQL server. Used if connection_string is not provided.
            port: The port number to connect to at the server host. Used if connection_string is not provided.
            dbname: The database name. Used if connection_string is not provided.
            username: The username to connect as. Used if connection_string is not provided.
            password: The user's password. Used if connection_string is not provided.
            connect_timeout: Maximum wait for connection, in seconds. The default is 10 seconds.

        Returns:
            A psycopg.Connection object representing the established connection.

        Raises:
            PermissionError if no credentials are supplied
            psycopg.Error: If an error occurs while trying to connect to the database.
        """
        try:
            if conn:
                self.client = conn
            elif connection_string:
                parsed_connection = urllib.parse.urlparse(connection_string)
                encoded_username = urllib.parse.quote(parsed_connection.username, safe="")
                encoded_password = urllib.parse.quote(parsed_connection.password, safe="")
                encoded_password = f":{encoded_password}@"
                encoded_host = urllib.parse.quote(parsed_connection.hostname, safe="")
                encoded_port = f":{parsed_connection.port}"
                encoded_database = urllib.parse.quote(parsed_connection.path[1:], safe="")
                connection_string_encoded = (
                    f"{parsed_connection.scheme}://{encoded_username}{encoded_password}"
                    f"{encoded_host}{encoded_port}/{encoded_database}"
                )
                self.client = psycopg.connect(conninfo=connection_string_encoded, autocommit=True)
            elif host:
                connection_string = ""
                if host:
                    encoded_host = urllib.parse.quote(host, safe="")
                    connection_string += f"host={encoded_host} "
                if port:
                    connection_string += f"port={port} "
                if dbname:
                    encoded_database = urllib.parse.quote(dbname, safe="")
                    connection_string += f"dbname={encoded_database} "
                if username:
                    encoded_username = urllib.parse.quote(username, safe="")
                    connection_string += f"user={encoded_username} "
                if password:
                    encoded_password = urllib.parse.quote(password, safe="")
                    connection_string += f"password={encoded_password} "

                self.client = psycopg.connect(
                    conninfo=connection_string,
                    connect_timeout=connect_timeout,
                    autocommit=True,
                )
            else:
                logger.error("Credentials were not supplied...")
                raise PermissionError
            self.client.execute("CREATE EXTENSION IF NOT EXISTS vector")
        except psycopg.Error as e:
            logger.error("Error connecting to the database: ", e)
            raise e
        return self.client

    def create_collection(
        self, collection_name: str, overwrite: bool = False, get_or_create: bool = True
    ) -> Collection:
        """
        Create a collection in the vector database.
        Case 1. if the collection does not exist, create the collection.
        Case 2. the collection exists, if overwrite is True, it will overwrite the collection.
        Case 3. the collection exists and overwrite is False, if get_or_create is True, it will get the collection,
            otherwise it raise a ValueError.

        Args:
            collection_name: str | The name of the collection.
            overwrite: bool | Whether to overwrite the collection if it exists. Default is False.
            get_or_create: bool | Whether to get the collection if it exists. Default is True.

        Returns:
            Collection | The collection object.
        """
        try:
            if self.active_collection and self.active_collection.name == collection_name:
                collection = self.active_collection
            else:
                collection = self.get_collection(collection_name)
        except ValueError:
            collection = None
        if collection is None:
            collection = Collection(
                client=self.client,
                collection_name=collection_name,
                embedding_function=self.embedding_function,
                get_or_create=get_or_create,
                metadata=self.metadata,
            )
            collection.set_collection_name(collection_name=collection_name)
            collection.create_collection(collection_name=collection_name)
            return collection
        elif overwrite:
            self.delete_collection(collection_name)
            collection = Collection(
                client=self.client,
                collection_name=collection_name,
                embedding_function=self.embedding_function,
                get_or_create=get_or_create,
                metadata=self.metadata,
            )
            collection.set_collection_name(collection_name=collection_name)
            collection.create_collection(collection_name=collection_name)
            return collection
        elif get_or_create:
            return collection
        elif not collection.table_exists(table_name=collection_name):
            collection = Collection(
                client=self.client,
                collection_name=collection_name,
                embedding_function=self.embedding_function,
                get_or_create=get_or_create,
                metadata=self.metadata,
            )
            collection.set_collection_name(collection_name=collection_name)
            collection.create_collection(collection_name=collection_name)
            return collection
        else:
            raise ValueError(f"Collection {collection_name} already exists.")

    def get_collection(self, collection_name: str = None) -> Collection:
        """
        Get the collection from the vector database.

        Args:
            collection_name: str | The name of the collection. Default is None. If None, return the
                current active collection.

        Returns:
            Collection | The collection object.
        """
        if collection_name is None:
            if self.active_collection is None:
                raise ValueError("No collection is specified.")
            else:
                logger.debug(
                    f"No collection is specified. Using current active collection {self.active_collection.name}."
                )
        else:
            if not (self.active_collection and self.active_collection.name == collection_name):
                self.active_collection = Collection(
                    client=self.client,
                    collection_name=collection_name,
                    embedding_function=self.embedding_function,
                )
        return self.active_collection

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete the collection from the vector database.

        Args:
            collection_name: str | The name of the collection.

        Returns:
            None
        """
        if self.active_collection:
            self.active_collection.delete_collection(collection_name)
        else:
            collection = self.get_collection(collection_name)
            collection.delete_collection(collection_name)
        if self.active_collection and self.active_collection.name == collection_name:
            self.active_collection = None

    def _batch_insert(
        self, collection: Collection, embeddings=None, ids=None, metadatas=None, documents=None, upsert=False
    ) -> None:
        batch_size = int(PGVECTOR_MAX_BATCH_SIZE)
        default_metadata = {"hnsw:space": "ip", "hnsw:construction_ef": 32, "hnsw:M": 16}
        default_metadatas = [default_metadata] * min(batch_size, len(documents))
        for i in range(0, len(documents), min(batch_size, len(documents))):
            end_idx = i + min(batch_size, len(documents) - i)
            collection_kwargs = {
                "documents": documents[i:end_idx],
                "ids": ids[i:end_idx],
                "metadatas": metadatas[i:end_idx] if metadatas else default_metadatas,
                "embeddings": embeddings[i:end_idx] if embeddings else None,
            }
            if upsert:
                collection.upsert(**collection_kwargs)
            else:
                collection.add(**collection_kwargs)

    def insert_docs(self, docs: List[Document], collection_name: str = None, upsert: bool = False) -> None:
        """
        Insert documents into the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents. Each document is a TypedDict `Document`.
            collection_name: str | The name of the collection. Default is None.
            upsert: bool | Whether to update the document if it exists. Default is False.
            kwargs: Dict | Additional keyword arguments.

        Returns:
            None
        """
        if not docs:
            return
        if docs[0].get("content") is None:
            raise ValueError("The document content is required.")
        if docs[0].get("id") is None:
            raise ValueError("The document id is required.")
        documents = [doc.get("content") for doc in docs]
        ids = [doc.get("id") for doc in docs]

        collection = self.get_collection(collection_name)
        if docs[0].get("embedding") is None:
            logger.debug(
                "No content embedding is provided. "
                "Will use the VectorDB's embedding function to generate the content embedding."
            )
            embeddings = None
        else:
            embeddings = [doc.get("embedding") for doc in docs]
        if docs[0].get("metadata") is None:
            metadatas = None
        else:
            metadatas = [doc.get("metadata") for doc in docs]

        self._batch_insert(collection, embeddings, ids, metadatas, documents, upsert)

    def update_docs(self, docs: List[Document], collection_name: str = None) -> None:
        """
        Update documents in the collection of the vector database.

        Args:
            docs: List[Document] | A list of documents.
            collection_name: str | The name of the collection. Default is None.

        Returns:
            None
        """
        self.insert_docs(docs, collection_name, upsert=True)

    def delete_docs(self, ids: List[ItemID], collection_name: str = None) -> None:
        """
        Delete documents from the collection of the vector database.

        Args:
            ids: List[ItemID] | A list of document ids. Each id is a typed `ItemID`.
            collection_name: str | The name of the collection. Default is None.
            kwargs: Dict | Additional keyword arguments.

        Returns:
            None
        """
        collection = self.get_collection(collection_name)
        collection.delete(ids=ids, collection_name=collection_name)

    def retrieve_docs(
        self,
        queries: List[str],
        collection_name: str = None,
        n_results: int = 10,
        distance_threshold: float = -1,
    ) -> QueryResults:
        """
        Retrieve documents from the collection of the vector database based on the queries.

        Args:
            queries: List[str] | A list of queries. Each query is a string.
            collection_name: str | The name of the collection. Default is None.
            n_results: int | The number of relevant documents to return. Default is 10.
            distance_threshold: float | The threshold for the distance score, only distance smaller than it will be
                returned. Don't filter with it if < 0. Default is -1.
            kwargs: Dict | Additional keyword arguments.

        Returns:
            QueryResults | The query results. Each query result is a list of list of tuples containing the document and
                the distance.
        """
        collection = self.get_collection(collection_name)
        if isinstance(queries, str):
            queries = [queries]
        results = collection.query(
            query_texts=queries,
            n_results=n_results,
            distance_threshold=distance_threshold,
        )
        logger.debug(f"Retrieve Docs Results:\n{results}")
        return results

    def get_docs_by_ids(
        self, ids: List[ItemID] = None, collection_name: str = None, include=None, **kwargs
    ) -> List[Document]:
        """
        Retrieve documents from the collection of the vector database based on the ids.

        Args:
            ids: List[ItemID] | A list of document ids. If None, will return all the documents. Default is None.
            collection_name: str | The name of the collection. Default is None.
            include: List[str] | The fields to include. Default is None.
                If None, will include ["metadatas", "documents"], ids will always be included.
            kwargs: dict | Additional keyword arguments.

        Returns:
            List[Document] | The results.
        """
        collection = self.get_collection(collection_name)
        include = include if include else ["metadatas", "documents"]
        results = collection.get(ids, include=include, **kwargs)
        logger.debug(f"Retrieve Documents by ID Results:\n{results}")
        return results
