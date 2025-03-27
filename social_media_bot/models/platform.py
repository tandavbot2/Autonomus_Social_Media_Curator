from enum import Enum

class Platform(str, Enum):
    """Platform enum with string values for better serialization"""
    DEVTO = "dev.to"
    MASTODON = "mastodon"
    REDDIT = "reddit" 