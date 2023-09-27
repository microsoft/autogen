import regex as re


def strip_punctuation(uni):
    """Strips punctuation from a unicode string. Returns the new unicode.

    Args:
        uni (unicode)

    Returns:
        unicode
    """
    return re.sub(r"\p{P}+", " ", uni)


def strip_whitespace(uni):
    """Strips all whitespace from a unicode string.

    Args:
        uni (unicode)

    Returns:
        unicode
    """
    return re.sub(r"\s+", "", uni)


def find_sublist(l, sublist):
    """Returns the index of the first occurence of sublist in the list l if
    it exists, otherwise -1. Like string.find

    Args:
        l (list[Object]):
        sublist (list[Object])

    Returns
        int
    """
    for i in range(len(l)):
        # Check index 0 first for optimization
        if l[i] == sublist[0] and l[i : i + len(sublist)] == sublist:
            return i
    return -1


class Phrase(object):
    """Represents a phrase and its tokenization.
    Uses regex-based tokenization copied from nltk.tokenize.RegexpTokenizer.

    Tokenization is computed lazily.
    """

    # I like "trains". --> [I, like, ", trains, ", .]
    TOKENIZER = re.compile(r"\w+|[^\w\s]", re.UNICODE | re.MULTILINE | re.DOTALL)

    def __init__(self, text):
        """Initialize a Phrase.

        Args:
            text (str or unicode)
        """
        self._text = str(text)
        self._tokens = None

    @property
    def text(self):
        return self._text

    def _tokenize(self):
        self._tokens = []
        self._token_spans = []
        for m in self.TOKENIZER.finditer(self._text):
            self._tokens.append(m.group())
            self._token_spans.append(m.span())
        self._tokens = tuple(self._tokens)
        self._token_spans = tuple(self._token_spans)

    @property
    def tokens(self):
        """Return the tuple of tokens.

        Returns:
            tuple(unicode)
        """
        if self._tokens is None:
            self._tokenize()
        return self._tokens

    def detokenize(self, start, end):
        """Return the substring of the original string that corresponds
        to tokens[start:end].

        Args:
            start (int)
            end (int)
        Returns:
            unicode
        """
        if self._tokens is None:
            self._tokenize()
        return self._text[self._token_spans[start][0] : self._token_spans[end - 1][1]]

    def __repr__(self):
        return repr(self._text)

    def __str__(self):
        return str(self._text)

    def __unicode__(self):
        return self._text

    # Let's not define __len__ since it's ambiguous


def word_tokenize(text):
    """Tokenize without keeping the mapping to the original string.

    Args:
        text (str or unicode)
    Return:
        list[unicode]
    """
    return Phrase.TOKENIZER.findall(text)
