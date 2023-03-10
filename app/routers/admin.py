from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from .. import models, schemas, utils, oauth2, func
from sqlalchemy.orm import Session
from ..database import get_db
from uuid import uuid4
from typing import List
from datetime import datetime
from jose import JWTError, jwt

router = APIRouter(
    prefix="/admin", # / = /{id}
    tags=['Admin'] # group requests
)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Response)
def create_admin(admin: schemas.AdminCreate, db: Session= Depends(get_db)):
    hashed_password = utils.hash(admin.password)
    admin.password = hashed_password
    new_admin = models.Admin(**admin.dict())
    admin_query = db.query(models.Admin).filter((models.Admin.username==admin.username)|
    (models.Admin.email==admin.username))
    found_admin = admin_query.first()
    if found_admin:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
            detail=f"Admin already exist.")
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    
    return {
        "status": "Registration successfull",
        "data": "Admin has be created"
    }

# verify admin token
@router.get('/check-token', status_code=status.HTTP_200_OK)
def verify_token(token: str = Depends(oauth2.oauth2_scheme)):
    try:
        jwt.decode(token, oauth2.SECRET_KEY, algorithms=[oauth2.ALGORITHM])

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})

# getting all customer orders
@router.get("/orders" )
def get_orders(db: Session = Depends(get_db), current_admin: int=Depends(oauth2.get_current_user)): 
    orders = db.query(models.Order).all()

    if not orders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
        detail=f"There are no orders")        

    full_orders = []
    for order in orders:
        order_items = db.query(models.OrderItem).filter(models.OrderItem.order_id==order.id).all()
        for order_item in order_items:
            item = db.query(models.Item).filter(models.Item.id==order_item.item_id).first()
            full_orders.append({
                    "order_id": order.id,
                    "customer_id": order.customer_id,
                    "item_name": item.name,
                    "quantity": order_item.quantity,
                    "total_price": order_item.total_price,
                    "status": order.status,
                    "order_date": order.order_date
                })

    if full_orders == []:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
        detail=f"There are no orders") 
    
    return full_orders

# confirm email and reset password
@router.put('/verify', status_code=status.HTTP_200_OK, response_model=schemas.Response)
def check_email(email: schemas.EmailCheck, db: Session=Depends(get_db)):
    
    admin_query = db.query(models.Admin).filter(models.Admin.email==email.email)
    admin = admin_query.first()

    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"This email is not recognized.")

    try:
        new_password = func.generate_code(8)
        hashed_password = utils.hash(new_password)
        password = hashed_password

        admin_query.update({"password": password}, synchronize_session=False)
        db.commit()

        return {
                "status": "ok", 
                "data": new_password
                }

    except:
        return {"status": "error"}

# update password
@router.put("/update_password", response_model=schemas.Response)
def update_customerPswrd(password: schemas.PasswordEdit, db: Session=Depends(get_db), current_admin: int=Depends(oauth2.get_current_user)):

    admin_query = db.query(models.Admin).filter(models.Admin.id==current_admin.id)
    admin = admin_query.first()

    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Customer was not found.")

    if password.password == '':
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    hashed_password = utils.hash(password.password)
    password = hashed_password
    try:
        admin_query.update({"password":password}, synchronize_session=False)
        db.commit()
        return {
        "status": "ok",
        "data": "Password reset succesfull"
    }
    except:
        return {"status": "error"}

@router.get("/{id}", response_model=schemas.AdminOut)
def get_admins(id: int, db: Session=Depends(get_db), current_admin: int=Depends(oauth2.get_current_user)):
    admin = db.query(models.Admin).filter(models.Admin.id==id).first()

    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Admin with the id: {id} was not found.")

    if admin.id != current_admin.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
        detail=f"Not authorized to perform this action")

    return admin