from bing_browser import BingTextBrowser
from google_browser import GoogleTextBrowser


class TextBrowserCreator:
    """Creator class for creating different text browsers at runtime. Make sure to add newly registered browsers here"""
    
    browser_classes = {
        'BingTextBrowser': BingTextBrowser,
        'GoogleTextBrowser': GoogleTextBrowser
    }

    @classmethod
    def create_browser(cls, name: str):
        """Factory method to create a text browser instance based on the name."""
        if name in cls.browser_classes:
            return cls.browser_classes[name]()
        else:
            raise ValueError(f"Unknown browser name: {name}")