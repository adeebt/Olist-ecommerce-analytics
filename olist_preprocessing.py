# ============================================================
# OLIST E-COMMERCE — Pre-processing & MySQL Load Script
# Author  : Adeeb
# Purpose : Clean all 9 CSVs and load into MySQL schema
# Requires: pip install pandas sqlalchemy pymysql numpy
# ============================================================

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIG — update credentials before running
# ============================================================

DB_USER     = 'root'
DB_PASSWORD = 'your_password_here'
DB_HOST     = 'localhost'
DB_PORT     = '3306'
DB_NAME     = 'olist_ecommerce'

# Path to the folder containing all 9 CSV files
DATA_PATH   = 'D:/Retail/Project2/'   # change if files are in a subfolder

# ============================================================
# CONNECTION
# ============================================================

engine = create_engine(
    f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4',
    echo=False
)

def log(msg):
    print(f'[INFO] {msg}')

def load_table(df, table_name, if_exists='append'):
    with engine.connect() as conn:
        conn.execute(text('SET FOREIGN_KEY_CHECKS = 0'))
        conn.execute(text(f'DELETE FROM {table_name}'))
        conn.execute(text('SET FOREIGN_KEY_CHECKS = 1'))
        conn.commit()
    df.to_sql(table_name, con=engine, if_exists=if_exists, index=False)
    log(f'Loaded {len(df):,} rows → {table_name}')


# ============================================================
# STEP 1 — LOAD RAW CSVs
# ============================================================

log('Loading raw CSVs...')

orders      = pd.read_csv(f'{DATA_PATH}olist_orders_dataset.csv')
items       = pd.read_csv(f'{DATA_PATH}olist_order_items_dataset.csv')
payments    = pd.read_csv(f'{DATA_PATH}olist_order_payments_dataset.csv')
reviews = pd.read_csv(f'{DATA_PATH}olist_order_reviews_dataset.csv', encoding='utf-8')
customers   = pd.read_csv(f'{DATA_PATH}olist_customers_dataset.csv')
products    = pd.read_csv(f'{DATA_PATH}olist_products_dataset.csv')
sellers     = pd.read_csv(f'{DATA_PATH}olist_sellers_dataset.csv')
geo         = pd.read_csv(f'{DATA_PATH}olist_geolocation_dataset.csv')
translation = pd.read_csv(f'{DATA_PATH}product_category_name_translation.csv')

log('All CSVs loaded.')


# ============================================================
# STEP 2 — CLEAN: dim_product_categories
# ============================================================

log('Cleaning dim_product_categories...')

# Add the 2 categories missing from the translation CSV
manual_additions = pd.DataFrame({
    'product_category_name':         [
        'portateis_cozinha_e_preparadores_de_alimentos',
        'pc_gamer'
    ],
    'product_category_name_english': [
        'portable_kitchen_appliances',
        'pc_gaming'
    ]
})

translation = pd.concat([translation, manual_additions], ignore_index=True)
translation.columns = ['category_name_pt', 'category_name_en']
translation = translation.drop_duplicates(subset='category_name_pt')

log(f'  Total categories: {len(translation)}')


# ============================================================
# STEP 3 — CLEAN: dim_customers
# ============================================================

log('Cleaning dim_customers...')

customers.columns = [
    'customer_id', 'customer_unique_id',
    'zip_code_prefix', 'city', 'state'
]

# No nulls, no duplicates — just type enforcement
customers['zip_code_prefix'] = customers['zip_code_prefix'].astype(int)
customers['city']  = customers['city'].str.strip().str.lower()
customers['state'] = customers['state'].str.strip().str.upper()

log(f'  Rows: {len(customers):,} | Nulls: {customers.isnull().sum().sum()}')


# ============================================================
# STEP 4 — CLEAN: dim_sellers
# ============================================================

log('Cleaning dim_sellers...')

sellers.columns = ['seller_id', 'zip_code_prefix', 'city', 'state']

sellers['zip_code_prefix'] = sellers['zip_code_prefix'].astype(int)
sellers['city']  = sellers['city'].str.strip().str.lower()
sellers['state'] = sellers['state'].str.strip().str.upper()

log(f'  Rows: {len(sellers):,} | Nulls: {sellers.isnull().sum().sum()}')


# ============================================================
# STEP 5 — CLEAN: dim_products
# ============================================================

log('Cleaning dim_products...')

products.columns = [
    'product_id', 'category_name_pt',
    'product_name_length', 'product_description_length',
    'product_photos_qty', 'weight_g',
    'length_cm', 'height_cm', 'width_cm'
]

# 610 null categories → 'uncategorized'
products['category_name_pt'] = products['category_name_pt'].fillna('uncategorized')

# Add uncategorized to translation table to maintain FK
uncategorized_row = pd.DataFrame({
    'category_name_pt': ['uncategorized'],
    'category_name_en': ['uncategorized']
})
translation = pd.concat([translation, uncategorized_row], ignore_index=True)
translation = translation.drop_duplicates(subset='category_name_pt')

# 2 null rows for weight/dimensions — fill with median
for col in ['weight_g', 'length_cm', 'height_cm', 'width_cm']:
    median_val = products[col].median()
    null_count = products[col].isnull().sum()
    products[col] = products[col].fillna(median_val)
    if null_count > 0:
        log(f'  Filled {null_count} nulls in {col} with median ({median_val})')

# Cast to int where appropriate
products['product_photos_qty']          = products['product_photos_qty'].fillna(0).astype(int)
products['product_name_length']         = products['product_name_length'].fillna(0).astype(int)
products['product_description_length']  = products['product_description_length'].fillna(0).astype(int)
products['weight_g']    = products['weight_g'].astype(int)
products['length_cm']   = products['length_cm'].astype(int)
products['height_cm']   = products['height_cm'].astype(int)
products['width_cm']    = products['width_cm'].astype(int)

log(f'  Rows: {len(products):,} | Nulls after clean: {products.isnull().sum().sum()}')


# ============================================================
# STEP 6 — CLEAN: dim_geolocation (deduplicate)
# ============================================================

log('Cleaning dim_geolocation...')

geo.columns = ['zip_code_prefix', 'lat', 'lng', 'city', 'state']

# Remove clearly erroneous coordinates
# Brazil bounding box: lat -35 to 5, lng -75 to -34
geo = geo[
    (geo['lat'].between(-36, 6)) &
    (geo['lng'].between(-75, -34))
]
outliers_removed = 1_000_163 - len(geo)
log(f'  Removed {outliers_removed:,} rows outside Brazil bounding box')

# Deduplicate: keep AVG lat/lng per zip, most frequent city/state
geo_coords = geo.groupby('zip_code_prefix').agg(
    avg_lat=('lat', 'mean'),
    avg_lng=('lng', 'mean')
).reset_index()

geo_labels = geo.groupby('zip_code_prefix').agg(
    city=('city',  lambda x: x.mode()[0]),
    state=('state', lambda x: x.mode()[0])
).reset_index()

geo_clean = geo_coords.merge(geo_labels, on='zip_code_prefix')
geo_clean['avg_lat'] = geo_clean['avg_lat'].round(6)
geo_clean['avg_lng'] = geo_clean['avg_lng'].round(6)
geo_clean['city']    = geo_clean['city'].str.strip().str.lower()
geo_clean['state']   = geo_clean['state'].str.strip().str.upper()

log(f'  Rows after dedup: {len(geo_clean):,} unique zip codes')


# ============================================================
# STEP 7 — CLEAN: fact_orders
# ============================================================

log('Cleaning fact_orders...')

orders.columns = [
    'order_id', 'customer_id', 'order_status',
    'order_purchase_timestamp', 'order_approved_at',
    'order_delivered_carrier_date', 'order_delivered_customer_date',
    'order_estimated_delivery_date'
]

# Parse all datetime columns
dt_cols = [
    'order_purchase_timestamp', 'order_approved_at',
    'order_delivered_carrier_date', 'order_delivered_customer_date',
    'order_estimated_delivery_date'
]
for col in dt_cols:
    orders[col] = pd.to_datetime(orders[col], errors='coerce')

# 1 delivered order has no payment record — flag it but keep it
# (payment data is missing; order itself is valid)
log(f'  Null counts:')
log(f'    order_approved_at: {orders["order_approved_at"].isnull().sum()}')
log(f'    order_delivered_carrier_date: {orders["order_delivered_carrier_date"].isnull().sum()}')
log(f'    order_delivered_customer_date: {orders["order_delivered_customer_date"].isnull().sum()}')
log(f'  NOTE: Nulls in delivery dates are expected for canceled/unavailable orders.')
log(f'  NOTE: Date anomalies (carrier before approval etc.) are filtered in vw_delivery_sla view — not dropped here.')

log(f'  Rows: {len(orders):,}')


# ============================================================
# STEP 8 — CLEAN: fact_order_items
# ============================================================

log('Cleaning fact_order_items...')

items.columns = [
    'order_id', 'order_item_id', 'product_id',
    'seller_id', 'shipping_limit_date', 'price', 'freight_value'
]

items['shipping_limit_date'] = pd.to_datetime(items['shipping_limit_date'], errors='coerce')
items['price']         = items['price'].round(2)
items['freight_value'] = items['freight_value'].round(2)

# No zero-price items exist in this dataset — confirmed in QC
# Freight = 0 kept as-is (may be free shipping promo)

log(f'  Rows: {len(items):,} | Nulls: {items.isnull().sum().sum()}')


# ============================================================
# STEP 9 — CLEAN: fact_order_payments
# ============================================================

log('Cleaning fact_order_payments...')

payments.columns = [
    'order_id', 'payment_sequential',
    'payment_type', 'payment_installments', 'payment_value'
]

# Remove junk rows: not_defined type, zero value, zero installments
before = len(payments)
payments = payments[
    (payments['payment_type'] != 'not_defined') &
    (payments['payment_value'] > 0) &
    (payments['payment_installments'] >= 1)
]
removed = before - len(payments)
log(f'  Removed {removed} junk payment rows (not_defined / zero value / zero installments)')
log(f'  Rows: {len(payments):,}')


# ============================================================
# STEP 10 — CLEAN: fact_order_reviews (deduplicate)
# ============================================================

log('Cleaning fact_order_reviews...')

reviews.columns = [
    'review_id', 'order_id', 'review_score',
    'review_comment_title', 'review_comment_message',
    'review_creation_date', 'review_answer_timestamp'
]

reviews['review_creation_date']    = pd.to_datetime(reviews['review_creation_date'],    errors='coerce')
reviews['review_answer_timestamp'] = pd.to_datetime(reviews['review_answer_timestamp'], errors='coerce')

# 551 orders have duplicate reviews → keep latest by review_answer_timestamp
before = len(reviews)
reviews = (
    reviews
    .sort_values('review_answer_timestamp', ascending=False)
    .drop_duplicates(subset='order_id', keep='first')
    .drop_duplicates(subset='review_id', keep='first')
    .reset_index(drop=True)
)
removed = before - len(reviews)
log(f'  Removed {removed} duplicate reviews (kept latest per order)')
log(f'  Rows: {len(reviews):,}')

# Trim comment fields
reviews['review_comment_title']   = reviews['review_comment_title'].str.strip()
reviews['review_comment_message'] = reviews['review_comment_message'].str.strip()
reviews['review_comment_message'] = reviews['review_comment_message'].fillna('')
reviews['review_comment_title']   = reviews['review_comment_title'].fillna('')


# ============================================================
# STEP 11 — A/B TEST SIMULATION
# ============================================================

log('Running A/B test simulation...')

# Scenario: Does reducing max installments to 3 EMIs affect AOV vs standard flow?
# Control   → no change (standard installment options)
# Treatment → capped at 3 EMIs in checkout (simulated)
#
# Method: randomly assign 50/50 split from delivered orders
# Seed fixed for reproducibility

delivered_orders = orders[orders['order_status'] == 'delivered'].copy()

np.random.seed(42)
delivered_orders['variant'] = np.where(
    np.random.rand(len(delivered_orders)) < 0.5,
    'control',
    'treatment'
)
delivered_orders['assigned_at'] = delivered_orders['order_purchase_timestamp']

ab_test = delivered_orders[['order_id', 'variant', 'assigned_at']].copy()

# Verify 50/50 split
split = ab_test['variant'].value_counts()
log(f'  Control:   {split["control"]:,} orders')
log(f'  Treatment: {split["treatment"]:,} orders')
log(f'  Total A/B test pool: {len(ab_test):,} orders')


# ============================================================
# STEP 12 — LOAD ALL TABLES TO MYSQL
# ============================================================

log('\nLoading tables to MySQL...')

# Load in FK-safe order: dimensions first, then facts

#load_table(translation, 'dim_product_categories')
#load_table(customers,   'dim_customers')
#load_table(sellers,     'dim_sellers')
#load_table(products,    'dim_products')
#load_table(geo_clean,   'dim_geolocation')

#load_table(orders,      'fact_orders')
#load_table(items,       'fact_order_items')
#load_table(payments,    'fact_order_payments')
load_table(reviews,     'fact_order_reviews')
load_table(ab_test,     'fact_ab_test')


# ============================================================
# STEP 13 — VALIDATION QUERIES
# ============================================================

log('\nRunning post-load validation...')

checks = {
    'dim_customers':          'SELECT COUNT(*) FROM dim_customers',
    'dim_sellers':            'SELECT COUNT(*) FROM dim_sellers',
    'dim_products':           'SELECT COUNT(*) FROM dim_products',
    'dim_product_categories': 'SELECT COUNT(*) FROM dim_product_categories',
    'dim_geolocation':        'SELECT COUNT(*) FROM dim_geolocation',
    'fact_orders':            'SELECT COUNT(*) FROM fact_orders',
    'fact_order_items':       'SELECT COUNT(*) FROM fact_order_items',
    'fact_order_payments':    'SELECT COUNT(*) FROM fact_order_payments',
    'fact_order_reviews':     'SELECT COUNT(*) FROM fact_order_reviews',
    'fact_ab_test':           'SELECT COUNT(*) FROM fact_ab_test',
}

with engine.connect() as conn:
    for table, query in checks.items():
        result = conn.execute(text(query)).scalar()
        print(f'  {table:<28} {result:>8,} rows')

log('\nValidation complete.')


# ============================================================
# STEP 14 — QUICK DATA QUALITY SUMMARY
# ============================================================

log('\nData Quality Summary:')
print(f'  Orders status distribution:')
print(orders['order_status'].value_counts().to_string())
print(f'\n  Payment type distribution (after cleaning):')
print(payments['payment_type'].value_counts().to_string())
print(f'\n  Review score distribution (after dedup):')
print(reviews['review_score'].value_counts().sort_index().to_string())
print(f'\n  A/B test variant split:')
print(ab_test['variant'].value_counts().to_string())

log('\n✅ All done. Database is ready for Power BI connection.')