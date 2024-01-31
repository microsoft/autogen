from autogen.coding import MarkdownCodeExtractor

_message_1 = """
Example:
```
print("hello extract code")
```
"""

_message_2 = """Example:
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

_message_3 = """
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

_message_4 = """
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

_message_5 = """
Test bash script:
```bash
echo 'hello world!'
```
"""

_message_6 = """
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

_message_7 = """
Test some message that has no code block.
"""


def test_extract_code() -> None:
    extractor = MarkdownCodeExtractor()

    code_blocks = extractor.extract_code_blocks(_message_1)
    assert len(code_blocks) == 1 and code_blocks[0].language == "python"

    code_blocks = extractor.extract_code_blocks(_message_2)
    assert len(code_blocks) == 2 and code_blocks[0].language == "python" and code_blocks[1].language == "python"

    code_blocks = extractor.extract_code_blocks(_message_3)
    assert len(code_blocks) == 1 and code_blocks[0].language == "python"

    code_blocks = extractor.extract_code_blocks(_message_4)
    assert len(code_blocks) == 1 and code_blocks[0].language == "python"

    code_blocks = extractor.extract_code_blocks(_message_5)
    assert len(code_blocks) == 1 and code_blocks[0].language == "bash"

    code_blocks = extractor.extract_code_blocks(_message_6)
    assert len(code_blocks) == 1 and code_blocks[0].language == ""

    code_blocks = extractor.extract_code_blocks(_message_7)
    assert len(code_blocks) == 0
