from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services import list_products, get_product

def test_products_have_twd_and_gallery():
    products=list_products()
    assert len(products)==11
    assert all(p['price_twd'] > 0 for p in products)
    assert all(len(p['gallery']) >= 2 for p in products)

def test_first_product_has_three_gallery_images():
    product=get_product(1)
    assert product['part_number']=='077-905-115-T'
    assert len(product['gallery'])==3
