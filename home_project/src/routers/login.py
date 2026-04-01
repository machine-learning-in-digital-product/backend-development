from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from dependencies.auth import JWT_COOKIE_NAME
from models.account import LoginRequest
from repositories.account import AccountRepository
from services.auth_service import auth_service

router = APIRouter(tags=["auth"])

account_repository = AccountRepository()


@router.post("/login")
async def login(body: LoginRequest):
    acc = await account_repository.find_by_login_and_password(
        body.login, body.password
    )
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    token = auth_service.create_access_token(acc["id"], acc["login"])
    response = JSONResponse(content={"status": "ok"})
    response.set_cookie(
        key=JWT_COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=86400 * 7,
        samesite="lax",
        path="/",
    )
    return response
