"""Custom exceptions for crawler module."""


class CrawlerException(Exception):
    """Base exception for crawler errors."""
    pass


class FetchException(CrawlerException):
    """Raised when fetching remote data fails."""
    pass


class ParseException(CrawlerException):
    """Raised when parsing/scraping data fails."""
    pass


class AnalysisException(CrawlerException):
    """Raised when analysis (e.g., AI evaluation) fails."""
    pass
