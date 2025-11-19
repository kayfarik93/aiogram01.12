import httpx
import os
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("API_URL")
API_URL = f"{URL}:8000"


async def register_user(name: str, email: str) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{API_URL}/reg", json={"name": name, "email": email})
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {e}")
            return False


async def get_all_users(order_by="id", direction="asc"):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/users", params={"order_by": order_by, "direction": direction})
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print("Ошибка при получении пользователей:", e)
            return []


async def get_user_by_id(user_id: int):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/users/{user_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print("Ошибка при получении пользователей:", e)
            return None


async def update_user_by_id(user_id: int, name: str, email: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(f"{API_URL}/users/{user_id}", json={"name": name, "email": email})
            return response.status_code == 200
        except Exception as e:
            print("Ошибка при получении пользователей:", e)
            return None


async def delete_user_by_id(user_id: int):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{API_URL}/users/{user_id}")
            return response.status_code == 200
        except Exception as e:
            print("Ошибка при получении пользователей:", e)
            return None