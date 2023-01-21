from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from .. import models, schemas, utils, oauth2, func
from sqlalchemy.orm import Session
from ..database import get_db, SessionLocal
from typing import List
from pydantic import EmailStr
import requests
import time
from jose import JWTError, jwt
import asyncio
from datetime import datetime, timedelta
from pytz import timezone

router = APIRouter(
    prefix="/customers",
    tags=['Customers'] 
)

# create new customer
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    hashed_password = utils.hash(customer.password)
    customer.password = hashed_password

    new_customer = models.Customer(**customer.dict())
    customer_query = db.query(models.Customer).filter((models.Customer.username==customer.username) |  
                    (models.Customer.email==customer.email))
    found_customer = customer_query.first()

    if found_customer:
        if found_customer.is_verified == True:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
            detail="Customer credentials already exist.")
        elif found_customer.is_verified != True:
            customer_query.delete(synchronize_session=False)
            db.commit()

    db.add(new_customer)
    db.commit()
    db.refresh(new_customer) 

    access_token = oauth2.create_access_token(data = {"customer_id": new_customer.id})

    return {"access_token": access_token, "token_type": "bearer"}

# confirm email
@router.put('/verify', response_model=schemas.CodeResponse)
def check_email(email: schemas.EmailCheck, db: Session=Depends(get_db)):
    
    customer_query = db.query(models.Customer).filter(models.Customer.email==email.email)
    customer = customer_query.first()

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"This email is not recognized.")

    if customer.is_verified != True:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, 
        detail= f"Please verify your email, then proceed.")

    try:
        code = func.generate_code(8)

        customer_query.update({"code": code}, synchronize_session=False)
        db.commit()

        return {
                "status": "ok", 
                "data": "Check your email inbox or spam for an 8 digit code", 
                "code": code, 
                "id": customer.id
                }

    except:
        return {"status": "error"}

# delete_code
@router.put("/delete_code", status_code=status.HTTP_200_OK)
def update_code(id: schemas.IdCheck, db: Session=Depends(get_db)):

    customer_query = db.query(models.Customer).filter(models.Customer.id==id.id)
    customer = customer_query.first()

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"This email is not recognized.")

    if customer.is_verified != True:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, 
        detail= f"Please verify your email, then proceed.")

    wait_time = 1 * 60

    time.sleep(wait_time)

    try:
        customer_query.update({"code": None}, synchronize_session=False)
        db.commit()
    except:
        return {"status": "error"}
    

# resend code
@router.put('/resend', response_model=schemas.ResendResponse)
def check_email(id: schemas.IdCheck, db: Session=Depends(get_db)):
    
    customer_query = db.query(models.Customer).filter(models.Customer.id==id.id)
    customer = customer_query.first()

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"This email is not recognized.")

    if customer.is_verified != True:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, 
        detail= f"Please verify your email, then proceed.")

    try:
        code = func.generate_code(8)

        customer_query.update({"code": code}, synchronize_session=False)
        db.commit()

        return {
                "status": "ok", 
                "data": "Check your email inbox or spam for an 8 digit code", 
                "code": code, 
                "email": customer.email
                }

    except:
        return {"status": "error"}

# verify code
@router.post('/verify_code', status_code=status.HTTP_200_OK)
def check_code(code: schemas.CodeCheck, db: Session=Depends(get_db)):

    customer = db.query(models.Customer).filter(models.Customer.code==code.code).first()

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Invalid Code")

    if customer.code == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Invalid Code")
        
    access_token = oauth2.create_access_token(data = {"customer_id": customer.id})

    return {"access_token": access_token, "token_type": "bearer"}
    
# update password
@router.put("/update_password", response_model=schemas.Response)
def update_customerPswrd(password: schemas.PasswordEdit, db: Session=Depends(get_db), current_customer: int=Depends(oauth2.get_current_user)):

    customer_query = db.query(models.Customer).filter(models.Customer.id==current_customer.id)
    customer = customer_query.first()

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Customer was not found.")

    if password.password == '':
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    hashed_password = utils.hash(password.password)
    password = hashed_password
    try:
        customer_query.update({"password":password}, synchronize_session=False)
        db.commit()
        return {
        "status": "ok",
        "data": "Password reset successfull"
    }
    except:
        return {"status": "error"}

# verify customers token
@router.get('/check-token', status_code=status.HTTP_200_OK)
def verify_token(token: str = Depends(oauth2.oauth2_scheme)):
    try:
        jwt.decode(token, oauth2.SECRET_KEY, algorithms=[oauth2.ALGORITHM])

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})


# fetch all customers
@router.get('/', response_model=List[schemas.CustomerOut])
def get_customer(db: Session = Depends(get_db), current_admin: int=Depends(oauth2.get_current_user)):
    customers = db.query(models.Customer).join(models.Profile, models.Customer.id==models.Profile.customer_id).all()
    admin = db.query(models.Admin).filter(models.Admin.id==current_admin.id).first()

    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
        detail=f"Not authorized to perform this action")

    all_customers = []
    for customer in customers:
        customer = func.full_profile(customer)
        all_customers.append(customer)

    return all_customers

# fetch all un-verified customers
@router.get('/unverified', response_model=int, status_code=status.HTTP_200_OK)
def get_unverifed(db: Session = Depends(get_db), current_admin: int=Depends(oauth2.get_current_user)):
    unverified_customers = db.query(models.Customer).filter(models.Customer.is_verified==False).all()
    if not unverified_customers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Nothing was found")

    return len(unverified_customers)

# delete all un-verified customers
@router.delete('/unverified/delete', status_code=status.HTTP_200_OK)
def delete_unverified(db: Session = Depends(get_db), current_admin: int=Depends(oauth2.get_current_user)):
    customer_query = db.query(models.Customer).filter(models.Customer.is_verified==False)
    unverified_customers = customer_query.all()
    if not unverified_customers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Nothing was found")

    customer_query.delete(synchronize_session=False)
    db.commit()
    
# fetch a customer profile
@router.get('/get_profile', response_model=schemas.CustomerOut)
def get_customer( db: Session = Depends(get_db), current_customer: int=Depends(oauth2.get_current_user)):

    customer = db.query(models.Customer).join(models.Profile, 
    models.Customer.id==models.Profile.customer_id).filter(models.Customer.id==current_customer.id).first()

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Customer with the id: {current_customer.id} was not found.")

    customer = func.full_profile(customer)

    return customer

# verify customer
@router.put("/verify_email", status_code=status.HTTP_200_OK)
def verify_customer(db: Session=Depends(get_db), current_customer: int=Depends(oauth2.get_current_user)):

    customer_query = db.query(models.Customer).filter(models.Customer.id==current_customer.id)
    customer = customer_query.first()

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Customer was not found.")

    if customer.is_verified == False:
        customer_query.update({"is_verified": True}, synchronize_session=False)
        db.commit()


# create customer profile
@router.post("/profile", status_code=status.HTTP_201_CREATED, response_model=schemas.Response)
def create_profile(profile: schemas.ProfileCreate, db: Session=Depends(get_db),
         current_customer: int=Depends(oauth2.get_current_user)):

    customer = db.query(models.Customer).filter(models.Customer.id==current_customer.id).first()

    existing_profile = db.query(models.Profile).filter(models.Profile.customer_id==current_customer.id).first()

    if not customer:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, 
        detail= f"Not authorized to perform this action")

    if existing_profile:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, 
        detail= f"Profie already exist, Please update.")

    if customer.is_verified == False:
        raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, 
        detail= f"Please verify your email, then proceed.")

    new_profile = models.Profile(customer_id=current_customer.id, **profile.dict())
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    return {
        "status": "ok",
        "data": "Profile registration completed"
    }

# update profile
@router.put("/profile/update", response_model=schemas.Response)
def update_profile(updated_profile: schemas.ProfileCreate, db: Session=Depends(get_db),
            current_customer: int=Depends(oauth2.get_current_user)):
    profile_query = db.query(models.Profile).filter(models.Profile.customer_id == current_customer.id)
    profile = profile_query.first()

    if profile == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
        detail=f"You don't have a profile, Please create one.")

    if profile.customer_id != current_customer.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
        detail=f"Not authorized to perform this action")

    profile_query.update(updated_profile.dict(), synchronize_session=False)

    db.commit()

    return {
        "status": "ok",
        "data": f"Profile updated sucessfully"
    }

# delete a customer
@router.delete("/{id}", response_model=schemas.Response)
def delete_profile(id: int, db: Session=Depends(get_db), current_admin: int=Depends(oauth2.get_current_user)):
    customer_query = db.query(models.Customer).filter(models.Customer.id==id)
    admin = db.query(models.Admin).filter(models.Admin.id==current_admin.id).first()
    customer = customer_query.first()

    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
        detail=f"Not authorized to perform this action")

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Customer with the id: {id} was not found.")

    customer_query.delete(synchronize_session=False)
    db.commit()

    return {
        "status": "ok",
        "data": f"Customer with id: {id} deleted sucessfully"
    }

async def get_unverified_users():
    with SessionLocal() as db: #create a database session and close session as soon as we are done
        unverified_customers = db.query(models.Customer).filter(models.Customer.is_verified==False).all()

    if not unverified_customers:
        return

    return unverified_customers

async def delete_user(id: int):
    with SessionLocal() as db:
        customer_query = db.query(models.Customer).filter(models.Customer.id==id)
        customer = customer_query.first()
        
    if not customer:
        pass

    customer_query.delete(synchronize_session=False)
    db.commit()

async def delete_unverified_users():
    stop_loop = True
    # get all unverified users
    unverified_users = await get_unverified_users()
    if unverified_users:
        while stop_loop:
            print('delete unverified user tasks has started')
            # Get current time
            now = datetime.now(timezone('UTC'))

            # Iterate through unverified users
            for user in unverified_users:
                # Check if user was created more than 24 hours ago
                user_created_time = user.created_at.replace(microsecond=0,tzinfo=timezone('UTC'))
                if now - user_created_time > timedelta(hours=6, minutes=10):
                    await delete_user(user.id)
                    print('Deleted')
    
            # get all unverified users again
            unverified_users = await get_unverified_users()
            # check if there are any unverified users
            if unverified_users:
                for pending_user in unverified_users:
                    user_created_time = pending_user.created_at.replace(microsecond=0,tzinfo=timezone('UTC'))
                    if now - user_created_time < timedelta(hours=6, minutes=10):
                        stop_loop = False

            # Sleep for 24 hours
            print('sleeping......')
            await asyncio.sleep(1 * 60)

# schedule task to run in the background
async def start_background_tasks():
    print('starting backgorund task')
    loop = asyncio.get_event_loop()
    loop.create_task(delete_unverified_users())
    print('started')

