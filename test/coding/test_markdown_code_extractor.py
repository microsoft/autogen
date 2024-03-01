from autogen.coding import MarkdownCodeExtractor


def test_extract_code1() -> None:
    extractor = MarkdownCodeExtractor()
    message = """Example:
```
print("hello extract code")
```
"""
    code_blocks = extractor.extract_code_blocks(message)
    assert len(code_blocks) == 1 and code_blocks[0].language == "python"


def test_extract_code2() -> None:
    extractor = MarkdownCodeExtractor()
    message = """Example:
```python
def scrape(url):
    import requests
    from bs4 import BeautifulSoup
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.find("title").text
    text = soup.find("div", {"id": "bodyContent"}).text
    return title, text
```
Test:
```python
url = "https://en.wikipedia.org/wiki/Web_scraping"
title, text = scrape(url)
print(f"Title: {title}")
print(f"Text: {text}")
```
"""
    code_blocks = extractor.extract_code_blocks(message)
    assert len(code_blocks) == 2 and code_blocks[0].language == "python" and code_blocks[1].language == "python"


def test_extract_code3() -> None:
    extractor = MarkdownCodeExtractor()
    message = """
Example:
   ```python
   def scrape(url):
       import requests
       from bs4 import BeautifulSoup
       response = requests.get(url)
       soup = BeautifulSoup(response.text, "html.parser")
       title = soup.find("title").text
       text = soup.find("div", {"id": "bodyContent"}).text
       return title, text
   ```
"""
    code_blocks = extractor.extract_code_blocks(message)
    assert len(code_blocks) == 1 and code_blocks[0].language == "python"


def test_extract_code4() -> None:
    extractor = MarkdownCodeExtractor()
    message = """
Example:
``` python
def scrape(url):
   import requests
   from bs4 import BeautifulSoup
   response = requests.get(url)
   soup = BeautifulSoup(response.text, "html.parser")
   title = soup.find("title").text
   text = soup.find("div", {"id": "bodyContent"}).text
   return title, text
```
""".replace(
        "\n", "\r\n"
    )

    code_blocks = extractor.extract_code_blocks(message)
    assert len(code_blocks) == 1 and code_blocks[0].language == "python"


def test_extract_code5() -> None:
    extractor = MarkdownCodeExtractor()
    message = """
Test bash script:
```bash
echo 'hello world!'
```
"""

    code_blocks = extractor.extract_code_blocks(message)
    assert len(code_blocks) == 1 and code_blocks[0].language == "bash"


def test_extract_code6() -> None:
    extractor = MarkdownCodeExtractor()
    message = """
Test some C# code, expecting ""
```
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace ConsoleApplication1
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("Hello World");
        }
    }
}
```
"""
    code_blocks = extractor.extract_code_blocks(message)
    assert len(code_blocks) == 1 and code_blocks[0].language == ""


def test_extract_code7() -> None:
    extractor = MarkdownCodeExtractor()
    message = """
Test some message that has no code block.
"""
    code_blocks = extractor.extract_code_blocks(message)
    assert len(code_blocks) == 0


def test_extract_code8() -> None:
    extractor = MarkdownCodeExtractor()
    message = """
Four backticks
````python
print(f"Text: {text}")
````
"""
    code_blocks = extractor.extract_code_blocks(message)
    assert len(code_blocks) == 1 and code_blocks[0].language == "python"


def test_extract_code9() -> None:
    extractor = MarkdownCodeExtractor()
    message = '''
Nested backticks
````python
print(f"""
```python
x = 1
```
""")
````
'''
    code_blocks = extractor.extract_code_blocks(message)
    assert len(code_blocks) == 1 and code_blocks[0].language == "python"
