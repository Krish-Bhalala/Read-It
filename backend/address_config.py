import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Addresses:
    """
    Configuration class to hold network addresses and ports used by the server and its components.
    Reads from environment variables with fallback defaults.
    """

    backend_addr: tuple[str, int] = (
        os.getenv("HOST", "0.0.0.0"),
        int(os.getenv("PORT", "10000")),
    )
    database_addr: tuple[str, int] = (
        os.getenv("DATABASE_HOST", "cormorant.cs.umanitoba.ca"),
        int(os.getenv("DATABASE_PORT", "50042")),
    )


class ValkeyConfig:
    """
    Configuration class for Valkey (Redis-compatible) database connection.
    """

    # Service URI from Aiven - format: rediss://user:password@host:port
    url: str = os.getenv("VALKEY_URL", "")

    # Use Valkey instead of professor's DB
    use_valkey: bool = os.getenv("USE_VALKEY", "true").lower() == "true"
