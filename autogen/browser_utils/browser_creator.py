from .bing_browser import BingTextBrowser
from .google_browser import GoogleTextBrowser


class TextBrowserEnum:
    """Enum class for creating different text browsers. Make sure to add newly registered browsers here"""
    
    bing = BingTextBrowser
    google = GoogleTextBrowser

    @classmethod
    def get_browser(cls, browser_str):
        return getattr(cls, browser_str)
   