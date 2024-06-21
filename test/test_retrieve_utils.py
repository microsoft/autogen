#!/usr/bin/env python3 -m pytest

"""
Unit test for retrieve_utils.py
"""
import pytest

try:
    import chromadb

    from autogen.retrieve_utils import (
        create_vector_db_from_dir,
        extract_text_from_pdf,
        get_files_from_dir,
        is_url,
        parse_html_to_markdown,
        query_vector_db,
        split_files_to_chunks,
        split_text_to_chunks,
    )
    from autogen.token_count_utils import count_token
except ImportError:
    skip = True
else:
    skip = False
import os

try:
    from unstructured.partition.auto import partition

    HAS_UNSTRUCTURED = True
except ImportError:
    HAS_UNSTRUCTURED = False

test_dir = os.path.join(os.path.dirname(__file__), "test_files")
expected_text = """AutoGen is an advanced tool designed to assist developers in harnessing the capabilities
of Large Language Models (LLMs) for various applications. The primary purpose of AutoGen is to automate and
simplify the process of building applications that leverage the power of LLMs, allowing for seamless
integration, testing, and deployment."""


@pytest.mark.skipif(skip, reason="dependency is not installed")
class TestRetrieveUtils:
    def test_split_text_to_chunks(self):
        long_text = "A" * 10000
        chunks = split_text_to_chunks(long_text, max_tokens=1000)
        assert all(count_token(chunk) <= 1000 for chunk in chunks)

    def test_split_text_to_chunks_raises_on_invalid_chunk_mode(self):
        with pytest.raises(AssertionError):
            split_text_to_chunks("A" * 10000, chunk_mode="bogus_chunk_mode")

    def test_split_text_to_chunks_overlapping(self):
        long_text = "\n".join([chr(i) for i in range(ord("A"), ord("Z"))])
        chunks = split_text_to_chunks(long_text, max_tokens=10, overlap=3)
        assert chunks == [
            "A\nB\nC\nD\nE\nF\nG\nH\nI",
            "G\nH\nI\nJ\nK\nL\nM\nN\nO",
            "M\nN\nO\nP\nQ\nR\nS\nT\nU",
            "S\nT\nU\nV\nW\nX\nY",
        ]
        chunks = split_text_to_chunks(long_text, max_tokens=10, overlap=0)
        assert chunks == ["A\nB\nC\nD\nE\nF\nG\nH\nI", "J\nK\nL\nM\nN\nO\nP\nQ\nR", "S\nT\nU\nV\nW\nX\nY"]

    def test_extract_text_from_pdf(self):
        pdf_file_path = os.path.join(test_dir, "example.pdf")
        assert "".join(expected_text.split()) == "".join(extract_text_from_pdf(pdf_file_path).strip().split())

    def test_split_files_to_chunks(self):
        pdf_file_path = os.path.join(test_dir, "example.pdf")
        txt_file_path = os.path.join(test_dir, "example.txt")
        chunks, _ = split_files_to_chunks([pdf_file_path, txt_file_path])
        assert all(
            isinstance(chunk, str) and "AutoGen is an advanced tool designed to assist developers" in chunk.strip()
            for chunk in chunks
        )

    def test_get_files_from_dir(self):
        files = get_files_from_dir(test_dir, recursive=False)
        assert all(os.path.isfile(file) for file in files)
        pdf_file_path = os.path.join(test_dir, "example.pdf")
        txt_file_path = os.path.join(test_dir, "example.txt")
        files = get_files_from_dir([pdf_file_path, txt_file_path])
        assert all(os.path.isfile(file) if isinstance(file, str) else os.path.isfile(file[0]) for file in files)
        files = get_files_from_dir(
            [
                pdf_file_path,
                txt_file_path,
                os.path.join(test_dir, "..", "..", "website/docs"),
                "https://raw.githubusercontent.com/microsoft/autogen/main/README.md",
            ],
            recursive=True,
        )
        assert all(os.path.isfile(file) if isinstance(file, str) else os.path.isfile(file[0]) for file in files)
        files = get_files_from_dir(
            [
                pdf_file_path,
                txt_file_path,
                os.path.join(test_dir, "..", "..", "website/docs"),
                "https://raw.githubusercontent.com/microsoft/autogen/main/README.md",
            ],
            recursive=True,
            types=["pdf", "txt"],
        )
        assert all(os.path.isfile(file) if isinstance(file, str) else os.path.isfile(file[0]) for file in files)
        assert len(files) == 3

    def test_is_url(self):
        assert is_url("https://www.example.com")
        assert not is_url("not_a_url")

    def test_create_vector_db_from_dir(self):
        db_path = "/tmp/test_retrieve_utils_chromadb.db"
        if os.path.exists(db_path):
            client = chromadb.PersistentClient(path=db_path)
        else:
            client = chromadb.PersistentClient(path=db_path)
            create_vector_db_from_dir(test_dir, client=client)

        assert client.get_collection("all-my-documents")

    def test_query_vector_db(self):
        db_path = "/tmp/test_retrieve_utils_chromadb.db"
        if os.path.exists(db_path):
            client = chromadb.PersistentClient(path=db_path)
        else:  # If the database does not exist, create it first
            client = chromadb.PersistentClient(path=db_path)
            create_vector_db_from_dir(test_dir, client=client)

        results = query_vector_db(["autogen"], client=client)
        assert isinstance(results, dict) and any("autogen" in res[0].lower() for res in results.get("documents", []))

    def test_custom_vector_db(self):
        try:
            import lancedb
        except ImportError:
            return
        from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent

        db_path = "/tmp/lancedb"

        def create_lancedb():
            db = lancedb.connect(db_path)
            data = [
                {"vector": [1.1, 1.2], "id": 1, "documents": "This is a test document spark"},
                {"vector": [0.2, 1.8], "id": 2, "documents": "This is another test document"},
                {"vector": [0.1, 0.3], "id": 3, "documents": "This is a third test document spark"},
                {"vector": [0.5, 0.7], "id": 4, "documents": "This is a fourth test document"},
                {"vector": [2.1, 1.3], "id": 5, "documents": "This is a fifth test document spark"},
                {"vector": [5.1, 8.3], "id": 6, "documents": "This is a sixth test document"},
            ]
            try:
                db.create_table("my_table", data)
            except OSError:
                pass

        class MyRetrieveUserProxyAgent(RetrieveUserProxyAgent):
            def query_vector_db(
                self,
                query_texts,
                n_results=10,
                search_string="",
            ):
                if query_texts:
                    vector = [0.1, 0.3]
                db = lancedb.connect(db_path)
                table = db.open_table("my_table")
                query = table.search(vector).where(f"documents LIKE '%{search_string}%'").limit(n_results).to_df()
                return {"ids": [query["id"].tolist()], "documents": [query["documents"].tolist()]}

            def retrieve_docs(self, problem: str, n_results: int = 20, search_string: str = ""):
                results = self.query_vector_db(
                    query_texts=[problem],
                    n_results=n_results,
                    search_string=search_string,
                )

                self._results = results
                print("doc_ids: ", results["ids"])

        ragragproxyagent = MyRetrieveUserProxyAgent(
            name="ragproxyagent",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=2,
            retrieve_config={
                "task": "qa",
                "chunk_token_size": 2000,
                "client": "__",
                "embedding_model": "all-mpnet-base-v2",
            },
        )

        create_lancedb()
        ragragproxyagent.retrieve_docs("This is a test document spark", n_results=10, search_string="spark")
        assert ragragproxyagent._results["ids"] == [[3, 1, 5]]

    def test_custom_text_split_function(self):
        def custom_text_split_function(text):
            return [text[: len(text) // 2], text[len(text) // 2 :]]

        db_path = "/tmp/test_retrieve_utils_chromadb.db"
        client = chromadb.PersistentClient(path=db_path)
        create_vector_db_from_dir(
            os.path.join(test_dir, "example.txt"),
            client=client,
            collection_name="mytestcollection",
            custom_text_split_function=custom_text_split_function,
            get_or_create=True,
            recursive=False,
        )
        results = query_vector_db(["autogen"], client=client, collection_name="mytestcollection", n_results=1)
        assert (
            "AutoGen is an advanced tool designed to assist developers in harnessing the capabilities"
            in results.get("documents")[0][0]
        )

    def test_retrieve_utils(self):
        client = chromadb.PersistentClient(path="/tmp/chromadb")
        create_vector_db_from_dir(
            dir_path="./website/docs",
            client=client,
            collection_name="autogen-docs",
            custom_text_types=["txt", "md", "rtf", "rst"],
            get_or_create=True,
        )
        results = query_vector_db(
            query_texts=[
                "How can I use AutoGen UserProxyAgent and AssistantAgent to do code generation?",
            ],
            n_results=4,
            client=client,
            collection_name="autogen-docs",
            search_string="AutoGen",
        )
        print(results["ids"][0])
        assert len(results["ids"][0]) == 4

    @pytest.mark.skipif(
        not HAS_UNSTRUCTURED,
        reason="do not run if unstructured is not installed",
    )
    def test_unstructured(self):
        pdf_file_path = os.path.join(test_dir, "example.pdf")
        txt_file_path = os.path.join(test_dir, "example.txt")
        word_file_path = os.path.join(test_dir, "example.docx")
        chunks, _ = split_files_to_chunks([pdf_file_path, txt_file_path, word_file_path])
        assert all(
            isinstance(chunk, str) and "AutoGen is an advanced tool designed to assist developers" in chunk.strip()
            for chunk in chunks
        )

    def test_parse_html_to_markdown(self):
        html = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Simple HTML Example</title>
            </head>
            <body>
                <h1>Hello, World!</h1>
                <p>This is a very simple HTML example.</p>
            </body>
            </html>
        """
        markdown = parse_html_to_markdown(html)
        assert (
            markdown
            == "# Simple HTML Example\n\nSimple HTML Example\n\nHello, World!\n=============\n\nThis is a very simple HTML example."
        )


if __name__ == "__main__":
    pytest.main()

    db_path = "/tmp/test_retrieve_utils_chromadb.db"
    if os.path.exists(db_path):
        os.remove(db_path)  # Delete the database file after tests are finished
