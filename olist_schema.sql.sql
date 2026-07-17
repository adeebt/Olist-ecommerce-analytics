-- ============================================================
-- OLIST E-COMMERCE ANALYTICS — MySQL Schema
-- Author  : Adeeb
-- Dataset : Brazilian E-Commerce (Olist) — 9 source CSVs
-- Design  : 3NF with analytical views on top
-- ============================================================

CREATE DATABASE IF NOT EXISTS olist_ecommerce;
USE olist_ecommerce;


-- ============================================================
-- DIMENSION TABLES
-- ============================================================

-- 1. dim_customers
--    Note: customer_id is per-order (not unique per person).
--    customer_unique_id is the true customer identifier.
--    One customer_unique_id can have multiple customer_ids
--    (max 17 across the dataset).
USE olist_ecommerce;

CREATE TABLE dim_product_categories (
    category_name_pt     VARCHAR(60)  NOT NULL,
    category_name_en     VARCHAR(60)  NOT NULL,
    CONSTRAINT pk_categories PRIMARY KEY (category_name_pt)
);

CREATE TABLE dim_customers (
    customer_id          CHAR(32)     NOT NULL,
    customer_unique_id   CHAR(32)     NOT NULL,
    zip_code_prefix      MEDIUMINT    NOT NULL,
    city                 VARCHAR(50)  NOT NULL,
    state                CHAR(2)      NOT NULL,
    CONSTRAINT pk_customers PRIMARY KEY (customer_id)
);

CREATE TABLE dim_sellers (
    seller_id            CHAR(32)     NOT NULL,
    zip_code_prefix      MEDIUMINT    NOT NULL,
    city                 VARCHAR(50)  NOT NULL,
    state                CHAR(2)      NOT NULL,
    CONSTRAINT pk_sellers PRIMARY KEY (seller_id)
);

CREATE TABLE dim_products (
    product_id                  CHAR(32)      NOT NULL,
    category_name_pt            VARCHAR(60)   NULL,
    product_name_length         SMALLINT      NULL,
    product_description_length  SMALLINT      NULL,
    product_photos_qty          TINYINT       NULL,
    weight_g                    MEDIUMINT     NULL,
    length_cm                   TINYINT       NULL,
    height_cm                   TINYINT       NULL,
    width_cm                    TINYINT       NULL,
    CONSTRAINT pk_products PRIMARY KEY (product_id),
    CONSTRAINT fk_product_category
        FOREIGN KEY (category_name_pt)
        REFERENCES dim_product_categories (category_name_pt)
);

CREATE TABLE dim_geolocation (
    zip_code_prefix   MEDIUMINT      NOT NULL,
    avg_lat           DECIMAL(10,6)  NOT NULL,
    avg_lng           DECIMAL(10,6)  NOT NULL,
    city              VARCHAR(60)    NOT NULL,
    state             CHAR(2)        NOT NULL,
    CONSTRAINT pk_geo PRIMARY KEY (zip_code_prefix)
);

CREATE TABLE fact_orders (
    order_id                        CHAR(32)     NOT NULL,
    customer_id                     CHAR(32)     NOT NULL,
    order_status                    VARCHAR(15)  NOT NULL,
    order_purchase_timestamp        DATETIME     NOT NULL,
    order_approved_at               DATETIME     NULL,
    order_delivered_carrier_date    DATETIME     NULL,
    order_delivered_customer_date   DATETIME     NULL,
    order_estimated_delivery_date   DATETIME     NOT NULL,
    CONSTRAINT pk_orders PRIMARY KEY (order_id),
    CONSTRAINT fk_order_customer
        FOREIGN KEY (customer_id)
        REFERENCES dim_customers (customer_id)
);

CREATE TABLE fact_order_items (
    order_id              CHAR(32)       NOT NULL,
    order_item_id         TINYINT        NOT NULL,
    product_id            CHAR(32)       NOT NULL,
    seller_id             CHAR(32)       NOT NULL,
    shipping_limit_date   DATETIME       NOT NULL,
    price                 DECIMAL(10,2)  NOT NULL,
    freight_value         DECIMAL(8,2)   NOT NULL,
    CONSTRAINT pk_order_items PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT fk_item_order
        FOREIGN KEY (order_id)
        REFERENCES fact_orders (order_id),
    CONSTRAINT fk_item_product
        FOREIGN KEY (product_id)
        REFERENCES dim_products (product_id),
    CONSTRAINT fk_item_seller
        FOREIGN KEY (seller_id)
        REFERENCES dim_sellers (seller_id)
);

CREATE TABLE fact_order_payments (
    order_id              CHAR(32)       NOT NULL,
    payment_sequential    TINYINT        NOT NULL,
    payment_type          VARCHAR(15)    NOT NULL,
    payment_installments  TINYINT        NOT NULL,
    payment_value         DECIMAL(10,2)  NOT NULL,
    CONSTRAINT pk_payments PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_payment_order
        FOREIGN KEY (order_id)
        REFERENCES fact_orders (order_id)
);

CREATE TABLE fact_order_reviews (
    review_id               CHAR(32)      NOT NULL,
    order_id                CHAR(32)      NOT NULL,
    review_score            TINYINT       NOT NULL,
    review_comment_title    VARCHAR(100)  NULL,
    review_comment_message  VARCHAR(500)  NOT NULL,
    review_creation_date    DATETIME      NOT NULL,
    review_answer_timestamp DATETIME      NOT NULL,
    CONSTRAINT pk_reviews PRIMARY KEY (review_id),
    CONSTRAINT fk_review_order
        FOREIGN KEY (order_id)
        REFERENCES fact_orders (order_id)
);

CREATE TABLE fact_ab_test (
    order_id     CHAR(32)     NOT NULL,
    variant      VARCHAR(10)  NOT NULL,
    assigned_at  DATETIME     NOT NULL,
    CONSTRAINT pk_ab_test PRIMARY KEY (order_id),
    CONSTRAINT fk_ab_order
        FOREIGN KEY (order_id)
        REFERENCES fact_orders (order_id)
);


-- ============================================================
-- ANALYTICAL VIEWS
-- ============================================================

-- View 1: vw_order_summary
-- Flat wide table joining all facts — base for most PBI queries
CREATE OR REPLACE VIEW vw_order_summary AS
SELECT
    o.order_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,

    -- Customer
    c.customer_unique_id,
    c.city                          AS customer_city,
    c.state                         AS customer_state,

    -- Financials (aggregated from items)
    SUM(i.price)                    AS gmv,
    SUM(i.freight_value)            AS total_freight,
    SUM(i.price + i.freight_value)  AS total_order_value,
    COUNT(i.order_item_id)          AS item_count,

    -- Payment
    p.payment_type,
    p.payment_installments,
    p.payment_value,

    -- Review
    r.review_score,

    -- SLA fields
    DATEDIFF(o.order_delivered_customer_date, o.order_purchase_timestamp)
                                    AS actual_delivery_days,
    DATEDIFF(o.order_estimated_delivery_date, o.order_purchase_timestamp)
                                    AS estimated_delivery_days,
    CASE
        WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
        THEN 1 ELSE 0
    END                             AS is_late_delivery

FROM fact_orders o
JOIN dim_customers           c ON o.customer_id   = c.customer_id
LEFT JOIN fact_order_items   i ON o.order_id      = i.order_id
LEFT JOIN fact_order_payments p ON o.order_id     = p.order_id
                               AND p.payment_sequential = 1   -- primary payment only
LEFT JOIN fact_order_reviews  r ON o.order_id     = r.order_id
GROUP BY
    o.order_id, o.order_status, o.order_purchase_timestamp,
    o.order_approved_at, o.order_delivered_carrier_date,
    o.order_delivered_customer_date, o.order_estimated_delivery_date,
    c.customer_unique_id, c.city, c.state,
    p.payment_type, p.payment_installments, p.payment_value,
    r.review_score;


-- View 2: vw_seller_performance
-- Seller scorecard — Page 3 of PBI report
CREATE OR REPLACE VIEW vw_seller_performance AS
SELECT
    s.seller_id,
    s.city                              AS seller_city,
    s.state                             AS seller_state,

    COUNT(DISTINCT o.order_id)          AS total_orders,
    SUM(i.price)                        AS total_gmv,
    ROUND(AVG(i.price), 2)              AS avg_order_value,

    ROUND(AVG(r.review_score), 2)       AS avg_review_score,

    -- Late delivery rate
    ROUND(
        SUM(CASE
            WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
            THEN 1 ELSE 0 END)
        / NULLIF(COUNT(DISTINCT o.order_id), 0) * 100
    , 1)                                AS late_delivery_pct,

    -- Cancellation rate
    ROUND(
        SUM(CASE WHEN o.order_status = 'canceled' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(DISTINCT o.order_id), 0) * 100
    , 1)                                AS cancellation_rate_pct,

    -- Composite seller score (weighted):
    -- 40% review score (normalized 0-100) + 30% on-time rate + 30% volume score
    ROUND(
        (COALESCE(AVG(r.review_score), 3) / 5 * 100 * 0.40)
        +
        ((1 - SUM(CASE
            WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
            THEN 1 ELSE 0 END)
            / NULLIF(COUNT(DISTINCT o.order_id), 0)) * 100 * 0.30)
        +
        (LEAST(COUNT(DISTINCT o.order_id) / 100, 1) * 100 * 0.30)
    , 1)                                AS seller_score

FROM dim_sellers s
JOIN fact_order_items  i ON s.seller_id  = i.seller_id
JOIN fact_orders       o ON i.order_id   = o.order_id
LEFT JOIN fact_order_reviews r ON o.order_id = r.order_id
GROUP BY s.seller_id, s.city, s.state;


-- View 3: vw_category_performance
-- Product & Category analytics — Page 4 of PBI report
CREATE OR REPLACE VIEW vw_category_performance AS
SELECT
    COALESCE(t.category_name_en, 'uncategorized') AS category_english,
    p.product_id,

    COUNT(DISTINCT o.order_id)                    AS total_orders,
    SUM(i.price)                                  AS total_gmv,
    ROUND(AVG(i.price), 2)                        AS avg_price,
    ROUND(AVG(i.freight_value), 2)                AS avg_freight,
    ROUND(AVG(i.freight_value / NULLIF(i.price, 0)) * 100, 1)
                                                  AS freight_to_price_pct,
    ROUND(AVG(r.review_score), 2)                 AS avg_review_score,
    ROUND(AVG(p.product_photos_qty), 1)           AS avg_photos_qty

FROM fact_order_items i
JOIN dim_products              p ON i.product_id       = p.product_id
LEFT JOIN dim_product_categories t ON p.category_name_pt = t.category_name_pt
JOIN fact_orders               o ON i.order_id         = o.order_id
LEFT JOIN fact_order_reviews   r ON o.order_id         = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY t.category_name_en, p.product_id;


-- View 4: vw_delivery_sla
-- Delivery analysis — Page 2 of PBI report
CREATE OR REPLACE VIEW vw_delivery_sla AS
SELECT
    o.order_id,
    c.state                                         AS customer_state,
    s.state                                         AS seller_state,

    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,

    DATEDIFF(o.order_approved_at,
             o.order_purchase_timestamp)            AS approval_days,

    DATEDIFF(o.order_delivered_carrier_date,
             o.order_approved_at)                   AS processing_days,

    DATEDIFF(o.order_delivered_customer_date,
             o.order_delivered_carrier_date)        AS transit_days,

    DATEDIFF(o.order_delivered_customer_date,
             o.order_purchase_timestamp)            AS total_delivery_days,

    DATEDIFF(o.order_estimated_delivery_date,
             o.order_purchase_timestamp)            AS estimated_days,

    DATEDIFF(o.order_delivered_customer_date,
             o.order_estimated_delivery_date)       AS delay_days,  -- negative = early

    CASE
        WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
        THEN 'Late'
        ELSE 'On Time'
    END                                             AS delivery_status

FROM fact_orders o
JOIN dim_customers          c ON o.customer_id = c.customer_id
JOIN fact_order_items       i ON o.order_id    = i.order_id
JOIN dim_sellers            s ON i.seller_id   = s.seller_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_delivered_carrier_date  IS NOT NULL
  AND o.order_approved_at             IS NOT NULL
  -- Exclude date logic anomalies
  AND o.order_delivered_carrier_date  >= o.order_approved_at
  AND o.order_delivered_customer_date >= o.order_delivered_carrier_date;


-- View 5: vw_payment_behavior
-- Payment & installment analysis — Page 5 of PBI report
CREATE OR REPLACE VIEW vw_payment_behavior AS
SELECT
    o.order_id,
    c.customer_unique_id,
    p.payment_type,
    p.payment_installments,
    p.payment_value,
    SUM(i.price)                    AS gmv,
    SUM(i.price + i.freight_value)  AS total_order_value,

    CASE
        WHEN p.payment_installments = 1  THEN '1 - Single'
        WHEN p.payment_installments <= 3 THEN '2-3 - Short EMI'
        WHEN p.payment_installments <= 6 THEN '4-6 - Medium EMI'
        ELSE '7+ - Long EMI'
    END                             AS installment_bucket,

    -- Repeat customer flag
    CASE
        WHEN COUNT(o2.order_id) OVER (
            PARTITION BY c.customer_unique_id
        ) > 1 THEN 'Repeat' ELSE 'One-Time'
    END                             AS customer_type

FROM fact_orders o
JOIN dim_customers          c  ON o.customer_id = c.customer_id
JOIN fact_order_payments    p  ON o.order_id    = p.order_id
                               AND p.payment_sequential = 1
JOIN fact_order_items       i  ON o.order_id    = i.order_id
JOIN fact_orders            o2 ON c.customer_id = o2.customer_id
WHERE o.order_status = 'delivered'
  AND p.payment_type != 'not_defined'
  AND p.payment_value > 0
GROUP BY
    o.order_id, c.customer_unique_id, p.payment_type,
    p.payment_installments, p.payment_value;


-- View 6: vw_ab_test_results
-- A/B Test — Page 6 of PBI report
-- Scenario: Does capping installments at 3 EMIs affect AOV?
-- Variant flag injected during Python pre-processing step.
-- Table: fact_ab_test (created separately via Python simulation script)
CREATE OR REPLACE VIEW vw_ab_test_results AS
SELECT
    ab.order_id,
    ab.variant,                         -- 'control' or 'treatment'
    ab.assigned_at,
    p.payment_installments,
    p.payment_type,
    p.payment_value,
    SUM(i.price)                        AS gmv,
    SUM(i.price + i.freight_value)      AS total_order_value,
    CASE WHEN o.order_status = 'delivered' THEN 1 ELSE 0 END
                                        AS converted
FROM fact_ab_test ab                    -- populated by Python script
JOIN fact_orders           o  ON ab.order_id = o.order_id
JOIN fact_order_payments   p  ON o.order_id  = p.order_id
                              AND p.payment_sequential = 1
JOIN fact_order_items      i  ON o.order_id  = i.order_id
WHERE p.payment_type != 'not_defined'
  AND p.payment_value > 0
GROUP BY
    ab.order_id, ab.variant, ab.assigned_at,
    p.payment_installments, p.payment_type, p.payment_value,
    o.order_status;


-- ============================================================
-- A/B TEST STAGING TABLE (populated by Python simulation)
-- ============================================================

CREATE TABLE IF NOT EXISTS fact_ab_test (
    order_id     CHAR(32)     NOT NULL,
    variant      VARCHAR(10)  NOT NULL,   -- 'control' or 'treatment'
    assigned_at  DATETIME     NOT NULL,
    CONSTRAINT pk_ab_test PRIMARY KEY (order_id),
    CONSTRAINT fk_ab_order
        FOREIGN KEY (order_id)
        REFERENCES fact_orders (order_id)
);


-- ============================================================
-- END OF SCHEMA
-- ============================================================


ALTER DATABASE olist_ecommerce CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 0;


TRUNCATE TABLE fact_order_reviews;
TRUNCATE TABLE fact_ab_test;
TRUNCATE TABLE fact_order_payments;
TRUNCATE TABLE fact_order_items;
TRUNCATE TABLE fact_orders;
TRUNCATE TABLE dim_geolocation;
TRUNCATE TABLE dim_products;
TRUNCATE TABLE dim_sellers;
TRUNCATE TABLE dim_customers;
TRUNCATE TABLE dim_product_categories;

SET FOREIGN_KEY_CHECKS = 1;

USE olist_ecommerce;

SET FOREIGN_KEY_CHECKS = 0;

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE fact_ab_test;
TRUNCATE TABLE fact_order_reviews;
SET FOREIGN_KEY_CHECKS = 1;

SELECT COUNT(*) FROM fact_order_reviews;

DROP TABLE IF EXISTS fact_ab_test;
DROP TABLE IF EXISTS fact_order_reviews;
DROP TABLE IF EXISTS fact_order_payments;
DROP TABLE IF EXISTS fact_order_items;
DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS dim_geolocation;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_sellers;
DROP TABLE IF EXISTS dim_customers;
DROP TABLE IF EXISTS dim_product_categories;

SET FOREIGN_KEY_CHECKS = 1;

ALTER TABLE fact_order_reviews 
MODIFY COLUMN review_comment_message VARCHAR(500) NULL;


SET GLOBAL sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

DROP VIEW IF EXISTS vw_order_summary;

CREATE VIEW vw_order_summary AS
SELECT
    o.order_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    c.customer_unique_id,
    c.city                          AS customer_city,
    c.state                         AS customer_state,
    SUM(i.price)                    AS gmv,
    SUM(i.freight_value)            AS total_freight,
    SUM(i.price + i.freight_value)  AS total_order_value,
    COUNT(i.order_item_id)          AS item_count,
    p.payment_type,
    p.payment_installments,
    p.payment_value,
    r.review_score,
    DATEDIFF(o.order_delivered_customer_date, o.order_purchase_timestamp)
                                    AS actual_delivery_days,
    DATEDIFF(o.order_estimated_delivery_date, o.order_purchase_timestamp)
                                    AS estimated_delivery_days,
    CASE
        WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
        THEN 1 ELSE 0
    END                             AS is_late_delivery
FROM fact_orders o
JOIN dim_customers           c ON o.customer_id   = c.customer_id
LEFT JOIN fact_order_items   i ON o.order_id      = i.order_id
LEFT JOIN fact_order_payments p ON o.order_id     = p.order_id
                               AND p.payment_sequential = 1
LEFT JOIN fact_order_reviews  r ON o.order_id     = r.order_id
GROUP BY
    o.order_id, o.order_status, o.order_purchase_timestamp,
    o.order_approved_at, o.order_delivered_carrier_date,
    o.order_delivered_customer_date, o.order_estimated_delivery_date,
    c.customer_unique_id, c.city, c.state,
    p.payment_type, p.payment_installments, p.payment_value,
    r.review_score;
    
    
    -- Check converted values
SELECT converted, COUNT(*) 
FROM vw_ab_test_results 
GROUP BY converted;

UPDATE ab_test_statistics 
SET metric = 'Gross Conversion (Cart Add Rate)'
WHERE metric LIKE 'Gross%';

UPDATE ab_test_statistics 
SET metric = 'Net Conversion (Purchase Rate)'
WHERE metric LIKE 'Net%';