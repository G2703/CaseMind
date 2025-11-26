"""
Custom exceptions for CaseMind application.
"""


class CaseMindException(Exception):
    """Base exception for CaseMind."""
    pass


class DocumentLoadError(CaseMindException):
    """Raised when document loading fails."""
    pass


class MetadataExtractionError(CaseMindException):
    """Raised when metadata extraction fails."""
    pass


class FactExtractionError(CaseMindException):
    """Raised when fact extraction fails."""
    pass


class EmbeddingError(CaseMindException):
    """Raised when embedding generation fails."""
    pass


class DocumentStoreError(CaseMindException):
    """Raised when document store operations fail."""
    pass


class DatabaseConnectionError(CaseMindException):
    """Raised when database connection fails."""
    pass


class TemplateNotFoundError(CaseMindException):
    """Raised when template is not found."""
    pass


class DuplicateDocumentError(CaseMindException):
    """Raised when duplicate document is detected."""
    pass


class ConfigurationError(CaseMindException):
    """Raised when configuration is invalid."""
    pass
