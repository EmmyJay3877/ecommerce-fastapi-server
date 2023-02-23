from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
import requests
from ..func import full_order
from .. import models, schemas, oauth2
from typing import Optional, List
from sqlalchemy.orm import Session
from ..database import get_db
from sqlalchemy import func
from jose import JWTError
import os

router = APIRouter(prefix="/orders", tags=['Orders'])

SERVER = os.environ.get("SERVER")

# create an order
@router.post("/{item_id}/{q}", status_code=status.HTTP_201_CREATED, response_model=schemas.OrderOut)
def create_order(item_id: int, q: int,  order: schemas.OrderCreate, db: Session = Depends(get_db), 
            current_customer: int=Depends(oauth2.get_current_user), ):
    customer = db.query(models.Customer).filter(models.Customer.id==current_customer.id).first()

    if not customer:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, 
        detail= f"Not Authorized")
    item = db.query(models.Item).filter(models.Item.id==item_id).first()
    new_order = models.Order(customer_id=current_customer.id)
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    order_item = models.OrderItem(item_id=item.id, order_id=new_order.id, quantity=q, total_price=item.price*q)
    db.add(order_item)
    db.commit()
    db.refresh(order_item)
    new_orderitem = full_order(new_order, order_item, item)
    return new_orderitem

# getting all orders
@router.get("/" , response_model=List[schemas.OrderOut])
def get_orders(db: Session = Depends(get_db), current_customer: int=Depends(oauth2.get_current_user)): 
    orders = db.query(models.Order).filter(models.Order.customer_id==current_customer.id, models.Order.status=='PENDING').all()

    if not orders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
        detail=f"You have no order")        

    full_orders = []
    for order in orders:
        order_items = db.query(models.OrderItem).filter(models.OrderItem.order_id==order.id).all()
        for order_item in order_items:
            item = db.query(models.Item).filter(models.Item.id==order_item.item_id).first()
            full_orders.append({
                    "orderitem_id": order_item.id,
                    "order_id": order.id,
                    "item_id": order_item.item_id,
                    "item_name": item.name,
                    "item_image": item.image,
                    "quantity": order_item.quantity,
                    "total_price": order_item.total_price,
                    "order_date": order.order_date
                })
    return full_orders

# update ordertiem quantity
@router.put("/orderitem/{id}/{q}", response_model=List[schemas.OrderOut])
def update_orderitem_quantity(id: int, q: int, db: Session = Depends(get_db), current_customer: int=Depends(oauth2.get_current_user)):

    customer = db.query(models.Customer).filter(models.Customer.id==current_customer.id).first()

    if not customer:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, 
        detail= f"Not Authorized")
    
    order_item_query = db.query(models.OrderItem).filter(models.OrderItem.id==id)
    order_item = order_item_query.first()

    if order_item == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
        detail=f"orderitem with id: {id} does not exist")

    item = db.query(models.Item).filter(models.Item.id==order_item.item_id).first()

    total_price = item.price * q

    order_item_query.update({"quantity": q, "total_price": total_price}, synchronize_session=False)

    db.commit()

    def get_all_orders():
        token = oauth2.create_access_token(data = {"customer_id": current_customer.id})
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{SERVER}/orders/", headers=headers)
        return response.json()

    all_orders = get_all_orders()
    return all_orders

# get order by order_id
@router.get("/{id}" , response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), current_customer: int=Depends(oauth2.get_current_user)): 
    order = db.query(models.Order).filter(models.Order.customer_id==current_customer.id, 
                models.Order.id==order_id).first()

    if not order:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, 
        detail= f"Not Authorized or Order does not exist")
    
    order_item = db.query(models.OrderItem).filter(models.OrderItem.order_id==order.id).first()
    item = db.query(models.Item).filter(models.Item.id==order_item.item_id).first()
    new_orderitem = full_order(order, order_item, item)
    return new_orderitem

# delete order by order_id
@router.delete("/{id}", response_model=schemas.Response)
def delete_order(id: int, db: Session=Depends(get_db), current_customer: int=Depends(oauth2.get_current_user)):
    order_query = db.query(models.Order).filter(models.Order.customer_id==current_customer.id, 
                models.Order.id==id)
    order = order_query.first()

    if order == None:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, 
        detail= f"Not Authorized or Order not found")

    order_query.delete(synchronize_session=False)
    db.commit()
    
    return {
        'status': 'ok',
        'data': 'Item deleted sucessfully'
    }


