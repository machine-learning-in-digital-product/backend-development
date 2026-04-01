from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from models.account import Account
from repositories.account import AccountRepository
from services.auth_service import auth_service

JWT_COOKIE_NAME = "access_token"


def get_account_repository() -> AccountRepository:
    return AccountRepository()


async def get_current_account(
    request: Request,
    repo: Annotated[AccountRepository, Depends(get_account_repository)],
) -> Account:
    token = request.cookies.get(JWT_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )
    try:
        data = auth_service.decode_token(token)
        account_id = int(data["sub"])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        )

    row = await repo.get_by_id(account_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    if row["is_blocked"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Аккаунт заблокирован",
        )
    return Account(id=row["id"], login=row["login"], is_blocked=row["is_blocked"])
