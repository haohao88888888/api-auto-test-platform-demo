from typing import Optional

from fastapi import FastAPI, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


app = FastAPI(title="Demo API for Automation Testing", version="0.1.0")


USERS = {
    1: {
        "id": 1,
        "username": "alice",
        "name": "Alice",
        "email": "alice@example.com",
        "role": "qa",
    },
    2: {
        "id": 2,
        "username": "bob",
        "name": "Bob",
        "email": "bob@example.com",
        "role": "developer",
    },
}

PASSWORDS = {
    "alice": "123456",
    "bob": "password",
}

ORDERS = [
    {"id": 1001, "user_id": 1, "title": "Keyboard", "amount": 199.0},
    {"id": 1002, "user_id": 1, "title": "Mouse", "amount": 99.0},
    {"id": 1003, "user_id": 2, "title": "Monitor", "amount": 1299.0},
]


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


def ok(data=None, message="success"):
    return {"code": 0, "message": message, "data": data}


def error(status_code: int, code: int, message: str):
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message, "data": None},
    )


def user_id_from_token(authorization: Optional[str]) -> Optional[int]:
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "", 1)
    if token == "demo-token-alice":
        return 1
    if token == "demo-token-bob":
        return 2
    return None


def authenticated_user_id(authorization: Optional[str]):
    token_user_id = user_id_from_token(authorization)
    if token_user_id is None:
        return error(401, 1002, "missing or invalid token")
    return token_user_id


def require_same_user(token_user_id: int, requested_user_id: int):
    if token_user_id != requested_user_id:
        return error(403, 1004, "forbidden: token user does not match requested user")
    return None


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/login")
def login(payload: LoginRequest):
    expected_password = PASSWORDS.get(payload.username)
    if expected_password != payload.password:
        return error(401, 1001, "invalid username or password")

    user = next(
        item for item in USERS.values() if item["username"] == payload.username
    )
    return ok(
        {
            "token": f"demo-token-{payload.username}",
            "user_id": user["id"],
            "username": payload.username,
        }
    )


@app.get("/users/{user_id}")
def get_user(user_id: int, authorization: Optional[str] = Header(default=None)):
    token_user_id = authenticated_user_id(authorization)
    if isinstance(token_user_id, JSONResponse):
        return token_user_id

    forbidden = require_same_user(token_user_id, user_id)
    if forbidden is not None:
        return forbidden

    user = USERS.get(user_id)
    if user is None:
        return error(404, 1003, "user not found")
    return ok(user)


@app.get("/orders")
def get_orders(
    user_id: int = Query(..., ge=1),
    authorization: Optional[str] = Header(default=None),
):
    token_user_id = authenticated_user_id(authorization)
    if isinstance(token_user_id, JSONResponse):
        return token_user_id

    forbidden = require_same_user(token_user_id, user_id)
    if forbidden is not None:
        return forbidden

    user_orders = [item for item in ORDERS if item["user_id"] == user_id]
    return ok(user_orders)
