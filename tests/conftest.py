import os

# Configure the application before test modules import it. Integration tests still
# skip unless the caller deliberately supplies a disposable PostgreSQL database.
test_url = os.getenv("TEST_DATABASE_URL")
if test_url:
    async_url = test_url if "+asyncpg" in test_url else test_url.replace("postgresql://", "postgresql+asyncpg://")
    os.environ["DATABASE_URL"] = async_url
    os.environ["SYNC_DATABASE_URL"] = test_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
