from pymongo import MongoClient
import xmltodict
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# Loading the environment variables from .env file
load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)

# Accessing the desired database and collection
db = client["lonca"]
products_collection = db["demo"]

# Reading the XML file
with open("lonca-sample.xml", "r", encoding="utf-8") as file:
    data = xmltodict.parse(file.read())

# Now, 'data' holds all product information in a Python dictionary
products = data['Products']['Product']

# Formatting the product to match the MongoDB schema
def format_product(product):
    # Handling the case where Description could be a string or missing
    description = product.get('Description', '')
    
    # If Description is a dictionary, extract the '#text' value
    if isinstance(description, dict):
        description_text = description.get('#text', '')
    else:
        # Otherwise, assume it's a string or empty
        description_text = description

    current_time = datetime.now(timezone.utc)
    # Attempt to retrieve 'createdAt' from XML if it exists
    # If 'createdAt' doesn't exist, use the current time
    created_at = product.get('createdAt', current_time)

    # Ensuring the comma is replaced with a period for float conversion
    return {
        "stock_code": product['@ProductId'],
        "name": product['@Name'].capitalize(),  # Capitalize the product name
        "price": float(product['ProductDetails']['ProductDetail'][0]['@Value'].replace(',', '.')),  # To Replace ',' with '.'
        "discounted_price": float(product['ProductDetails']['ProductDetail'][1]['@Value'].replace(',', '.')),  # To Replace ',' with '.'
        "product_type": product['ProductDetails']['ProductDetail'][2]['@Value'],
        "quantity": int(product['ProductDetails']['ProductDetail'][3]['@Value']),
        "color": [product['ProductDetails']['ProductDetail'][4]['@Value']],
        "series": product['ProductDetails']['ProductDetail'][5]['@Value'],
        "images": [img['@Path'] for img in product['Images']['Image']],
        "description": description_text,  # Using the correctly handled description
        "is_discounted": float(product['ProductDetails']['ProductDetail'][1]['@Value'].replace(',', '.')) < float(product['ProductDetails']['ProductDetail'][0]['@Value'].replace(',', '.')),  # Compare prices after replacing commas with periods
        "createdAt": created_at,  # Setting the current time as createdAt
        "updatedAt": current_time   # Setting the same time as updatedAt initially
    }

# Iterating through the products and insert them into MongoDB
for product in products:
    formatted_product = format_product(product)
    existing_product = products_collection.find_one({"stock_code": formatted_product["stock_code"]})
    
    if existing_product:
        # Build an update dictionary with fields that should be updated
        update_fields = {}
        
        # Compare fields and update only if there is a change
        for field in ["name", "price", "discounted_price", "product_type", "quantity", "color", "series", "images", "description", "is_discounted"]:
            if existing_product.get(field) != formatted_product[field]:
                update_fields[field] = formatted_product[field]

        # Always update the 'updatedAt' field
        update_fields["updatedAt"] = datetime.now(timezone.utc)
        
        # Only update if there are changes to be made
        if update_fields:
            products_collection.update_one(
                {"stock_code": formatted_product["stock_code"]},
                {"$set": update_fields}
            )
            print(f"Updated product {formatted_product['name']} with changes: {update_fields}.")
        else:
            print(f"No updates for product {formatted_product['name']}.")
    else:
        # Inserting the new product if it doesn't exist
        products_collection.insert_one(formatted_product)
        print(f"Inserted product {formatted_product['name']}.")

print("Insertion process completed!!!")
client.close()
