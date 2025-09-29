from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.app import crud, schemas
from api.app.database import get_db

router = APIRouter()

# DB ---------------------------------------------------------------------------------------

@router.post("/users/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_user(db, user)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/users/{id}", response_model=schemas.UserResponse)
def get_user(id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/users/{id}")
def delete_user(id: int, db: Session = Depends(get_db)):
    deleted_user = crud.delete_user(db, id)
    if not deleted_user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"User with ID: '{id}' deleted"}

