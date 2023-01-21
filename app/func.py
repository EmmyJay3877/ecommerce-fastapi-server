
def full_profile(customer):
    return {
        "id" :customer.id,
        "username" :customer.username,
        "email" :customer.email,
        "phone_number" :customer.profile.phone_number,
        "city" :customer.profile.city,
        "region" :customer.profile.region,
        "created_at" :customer.created_at
    }

def full_order(new_order, order_item, item):
    return {
                    "orderitem_id": order_item.id,
                    "order_id": new_order.id,
                    "item_id": order_item.item_id,
                    "item_name": item.name,
                    "item_image": item.image,
                    "quantity": order_item.quantity,
                    "total_price": order_item.total_price,
                    "order_date": new_order.order_date
            }

import random
import string

def generate_code(length):
  # create a list of all possible characters (numbers and letters)
  characters = string.digits + string.ascii_letters

  # create an empty string to store the code
  code = ""

  # choose `length` random characters from the list and add them to the code string
  for i in range(length):
    code += random.choice(characters)

  return code

