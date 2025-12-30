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
        os.getenv("BACKEND_HOST", "aviary.cs.umanitoba.ca"),
        int(os.getenv("BACKEND_PORT", "12345")),
    )
    database_addr: tuple[str, int] = (
        os.getenv("DATABASE_HOST", "cormorant.cs.umanitoba.ca"),
        int(os.getenv("DATABASE_PORT", "50042")),
    )
