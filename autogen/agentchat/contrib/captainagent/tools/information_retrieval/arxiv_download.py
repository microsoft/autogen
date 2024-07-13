import arxiv

from autogen.coding.func_with_reqs import with_requirements


@with_requirements(["arxiv"], ["arxiv"])
def arxiv_download(id_list: list, download_dir="./"):
    """
    Downloads PDF files from ArXiv based on a list of arxiv paper IDs.

    Args:
        id_list (list): A list of paper IDs to download. e.g. [2302.00006v1]
        download_dir (str, optional): The directory to save the downloaded PDF files. Defaults to './'.

    Returns:
        list: A list of paths to the downloaded PDF files.
    """
    paths = []
    for paper in arxiv.Client().results(arxiv.Search(id_list=id_list)):
        path = paper.download_pdf(download_dir, filename=paper.get_short_id() + ".pdf")
        paths.append(path)
        print("Paper id:", paper.get_short_id(), "Downloaded to:", path)
    return paths
