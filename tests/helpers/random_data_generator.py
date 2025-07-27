"""Random data generator for testing."""

import random
import string
from datetime import datetime, timedelta


class RandomDataGenerator:
    """Helper class for generating random data for testing."""

    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate a random string."""
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def random_int(min_val: int = 0, max_val: int = 100) -> int:
        """Generate a random integer."""
        return random.randint(min_val, max_val)

    @staticmethod
    def random_float(
        min_val: float = 0.0, max_val: float = 100.0, precision: int = 2
    ) -> float:
        """Generate a random float with specified precision."""
        value = random.uniform(min_val, max_val)
        return round(value, precision)

    @staticmethod
    def random_date(start_date: datetime = None, end_date: datetime = None) -> datetime:
        """Generate a random datetime between two datetime objects."""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()

        time_between_dates = end_date - start_date
        days_between_dates = time_between_dates.days
        random_number_of_days = random.randrange(days_between_dates)
        random_date = start_date + timedelta(days=random_number_of_days)
        return random_date

    @staticmethod
    def random_email() -> str:
        """Generate a random email address."""
        username = RandomDataGenerator.random_string(8)
        domain = RandomDataGenerator.random_string(5)
        return f"{username}@{domain}.com"
