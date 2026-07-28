CREATE VIEW revenue_by_product AS
SELECT
    products.product_id,
    products.product_name,
    ROUND(
        SUM(order_items.quantity * order_items.sale_price_cents) / 100.0,
        2
    ) AS revenue
FROM products
JOIN order_items
    ON order_items.product_id = products.product_id
JOIN orders
    ON orders.order_id = order_items.order_id
WHERE orders.order_status IN ('PAID', 'SHIPPED')
GROUP BY products.product_id, products.product_name;

CREATE VIEW margin_by_product AS
SELECT
    products.product_id,
    products.product_name,
    ROUND(
        SUM(order_items.quantity * order_items.sale_price_cents) / 100.0,
        2
    ) AS revenue,
    ROUND(
        SUM(order_items.quantity * products.cost_cents) / 100.0,
        2
    ) AS total_cost,
    ROUND(
        SUM(
            order_items.quantity
            * (order_items.sale_price_cents - products.cost_cents)
        ) / 100.0,
        2
    ) AS gross_margin
FROM products
JOIN order_items
    ON order_items.product_id = products.product_id
JOIN orders
    ON orders.order_id = order_items.order_id
WHERE orders.order_status IN ('PAID', 'SHIPPED')
GROUP BY products.product_id, products.product_name;

CREATE VIEW revenue_by_category AS
SELECT
    categories.category_name,
    ROUND(
        SUM(order_items.quantity * order_items.sale_price_cents) / 100.0,
        2
    ) AS revenue
FROM categories
JOIN products
    ON products.category_id = categories.category_id
JOIN order_items
    ON order_items.product_id = products.product_id
JOIN orders
    ON orders.order_id = order_items.order_id
WHERE orders.order_status IN ('PAID', 'SHIPPED')
GROUP BY categories.category_id, categories.category_name;

CREATE VIEW product_revenue_rank AS
SELECT
    product_id,
    product_name,
    revenue,
    RANK() OVER (ORDER BY revenue DESC) AS revenue_rank
FROM revenue_by_product;

CREATE VIEW dashboard_summary AS
SELECT
    ROUND(
        COALESCE(
            SUM(order_items.quantity * order_items.sale_price_cents),
            0
        ) / 100.0,
        2
    ) AS total_revenue,
    ROUND(
        COALESCE(
            SUM(
                order_items.quantity
                * (order_items.sale_price_cents - products.cost_cents)
            ),
            0
        ) / 100.0,
        2
    ) AS total_gross_margin,
    COUNT(DISTINCT orders.order_id) AS valid_orders,
    (
        SELECT COUNT(*)
        FROM products AS active_product
        WHERE active_product.active = 1
    ) AS active_products
FROM orders
JOIN order_items
    ON order_items.order_id = orders.order_id
JOIN products
    ON products.product_id = order_items.product_id
WHERE orders.order_status IN ('PAID', 'SHIPPED');
