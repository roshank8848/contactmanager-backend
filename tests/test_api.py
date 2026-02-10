import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings

# Use a separate test database if possible, or just the same one for now
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL.replace("contact_db", "contact_db_test")

# If using the same DB, be careful. 
# For this task, let's assume we can use a separate DB or just clear tables.
# But creating a new DB requires admin rights. 
# Let's stick to the existing DB but truncate tables or use transaction rollback.
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

@pytest_asyncio.fixture(scope="function")
async def db_session():
    # Create engine per test to avoid loop issues
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
        # Cleanup could go here (e.g. truncate tables)
        
    # Drop tables to clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_create_contact(client):
    response = await client.post(
        "/contacts/",
        json={
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "phone_number": "1234567890",
            "address": "123 Test St"
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_read_contacts(client):
    # Create a contact first
    await client.post(
        "/contacts/",
        json={
            "first_name": "Read",
            "last_name": "Me",
            "email": "read@example.com",
            "phone_number": "0000000000"
        },
    )
    
    response = await client.get("/contacts/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

@pytest.mark.asyncio
async def test_search_contacts(client):
    await client.post(
        "/contacts/",
        json={
            "first_name": "Search",
            "last_name": "Me",
            "email": "search@example.com",
            "phone_number": "1111111111"
        },
    )
    
    response = await client.get("/contacts/?search=Search")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["first_name"] == "Search"

@pytest.mark.asyncio
async def test_read_contact(client):
    create_response = await client.post(
        "/contacts/",
        json={
            "first_name": "Single",
            "last_name": "Contact",
            "email": "single@example.com",
            "phone_number": "2222222222"
        },
    )
    contact_id = create_response.json()["id"]
    
    response = await client.get(f"/contacts/{contact_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == contact_id

@pytest.mark.asyncio
async def test_update_contact(client):
    create_response = await client.post(
        "/contacts/",
        json={
            "first_name": "To",
            "last_name": "Update",
            "email": "update@example.com",
            "phone_number": "3333333333"
        },
    )
    contact_id = create_response.json()["id"]
    
    response = await client.put(
        f"/contacts/{contact_id}",
        json={
            "first_name": "Updated",
            "last_name": "User",
            "email": "update@example.com",
            "phone_number": "3333333333"
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Updated"

@pytest.mark.asyncio
async def test_delete_contact(client):
    create_response = await client.post(
        "/contacts/",
        json={
            "first_name": "To",
            "last_name": "Delete",
            "email": "delete@example.com",
            "phone_number": "4444444444"
        },
    )
    contact_id = create_response.json()["id"]
    
    response = await client.delete(f"/contacts/{contact_id}")
    assert response.status_code == 200
    
    # Verify deletion
    response = await client.get(f"/contacts/{contact_id}")
    assert response.status_code == 404
