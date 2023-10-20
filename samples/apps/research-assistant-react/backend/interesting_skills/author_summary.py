def author_summary(author_name, author_email):
    """
    This function searches for PDF papers written by the author, downloads them,
    converts them to text files and generates a 2 sentence summary for each.
    """
    import os
    import re
    import requests
    import lit_reviewer_mod

    # Search for PDF papers written by the author
    results = lit_reviewer_mod.bing_search(f"{author_name} {author_email} filetype:pdf")

    # Download the PDFs and save them with the specified format
    pdf_filenames = []
    pdf_urls = []
    for result in results:
        response = requests.get(result["url"])
        match = re.search(r"(\w+)-(\d{4})", result["url"])
        if match:
            filename = f"{match.group(1)}-{match.group(2)}.pdf"
        else:
            filename = result["url"].split("/")[-1]
        suffix = 1
        original_filename = filename
        while os.path.isfile(filename):
            filename = f"{original_filename[:-4]}_{suffix}.pdf"
            suffix += 1
        with open(filename, "wb") as f:
            f.write(response.content)
        pdf_filenames.append(filename)
        pdf_urls.append(result["url"])

    # Convert the PDFs to text files and generate a 2 sentence summary for each
    table = "| Filename | 2 Sentence Summary |\n| --- | --- |\n"
    for i, pdf_filename in enumerate(pdf_filenames):
        try:
            text_content = lit_reviewer_mod.extract_pdf_text(pdf_filename)
        except Exception as e:
            print(f"Skipping a file due to error: {e}")
            continue

        # Truncate the text content to fit within the model's maximum context length
        text_content = text_content[:16385]

        # Generate a 2 sentence summary of the contents
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": f"Summarize the following text in 2 sentences:\n{text_content}",
            },
        ]
        summary = lit_reviewer_mod.gpt3_5_turbo(messages)
        table += f"| [{pdf_filename}]({pdf_urls[i]}) | {summary} |\n"

    return table
