import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order, OrderItem, User

app = FastAPI(title="Tech Gadgets Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProductOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    price: float
    category: str
    brand: Optional[str] = None
    image: Optional[str] = None
    rating: Optional[float] = 0
    in_stock: bool

class OrderCreate(BaseModel):
    customer_name: str
    customer_email: str
    customer_address: str
    items: List[OrderItem]

@app.get("/")
def read_root():
    return {"message": "Tech Gadgets Store API"}

@app.get("/api/products", response_model=List[ProductOut])
def list_products(category: Optional[str] = None, q: Optional[str] = None):
    filter_query = {}
    if category:
        filter_query["category"] = category
    if q:
        filter_query["title"] = {"$regex": q, "$options": "i"}

    docs = get_documents("product", filter_query, limit=100)
    items: List[ProductOut] = []
    for d in docs:
        items.append(ProductOut(
            id=str(d.get("_id")),
            title=d.get("title"),
            description=d.get("description"),
            price=float(d.get("price", 0)),
            category=d.get("category", "Other"),
            brand=d.get("brand"),
            image=d.get("image"),
            rating=float(d.get("rating", 0)),
            in_stock=bool(d.get("in_stock", True))
        ))
    return items

@app.post("/api/products/seed")
def seed_products():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    existing = db["product"].count_documents({})
    if existing > 0:
        return {"message": "Products already seeded", "count": existing}

    sample_products = [
        {
            "title": "Gaming Laptop 15" ,
            "description": "High performance gaming laptop with RTX 4070",
            "price": 1799.99,
            "category": "Laptops",
            "brand": "Acer",
            "image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=1200&q=80",
            "rating": 4.6,
            "in_stock": True
        },
        {
            "title": "Noise Cancelling Headphones",
            "description": "Over-ear wireless ANC headphones",
            "price": 299.99,
            "category": "Audio",
            "brand": "Sony",
            "image": "https://images.unsplash.com/photo-1518441902117-f83d2c1d0f4a?w=1200&q=80",
            "rating": 4.7,
            "in_stock": True
        },
        {
            "title": "4K Action Camera",
            "description": "Waterproof action camera with stabilization",
            "price": 249.00,
            "category": "Cameras",
            "brand": "GoPro",
            "image": "https://images.unsplash.com/photo-1519183071298-a2962be96f83?w=1200&q=80",
            "rating": 4.5,
            "in_stock": True
        },
        {
            "title": "Smartphone Pro Max",
            "description": "Flagship smartphone with triple camera",
            "price": 999.00,
            "category": "Phones",
            "brand": "Apple",
            "image": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=1200&q=80",
            "rating": 4.8,
            "in_stock": True
        },
        {
            "title": "Mechanical Keyboard",
            "description": "RGB mechanical keyboard with hot-swappable keys",
            "price": 129.99,
            "category": "Accessories",
            "brand": "Keychron",
            "image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=1200&q=80",
            "rating": 4.4,
            "in_stock": True
        }
    ]

    for p in sample_products:
        create_document("product", p)

    return {"message": "Seeded products", "count": len(sample_products)}

@app.post("/api/orders")
def create_order(payload: OrderCreate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Calculate totals
    subtotal = sum(item.price * item.quantity for item in payload.items)
    tax = round(subtotal * 0.08, 2)
    total = round(subtotal + tax, 2)

    order_doc = Order(
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_address=payload.customer_address,
        items=[OrderItem(**i.model_dump()) for i in payload.items],
        subtotal=round(subtotal, 2),
        tax=tax,
        total=total,
    )

    order_id = create_document("order", order_doc)
    return {"order_id": order_id, "total": total}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
