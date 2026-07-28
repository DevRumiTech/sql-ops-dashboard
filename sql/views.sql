CREATE VIEW completed_order_lines AS
SELECT
    orders.order_id,
    orders.order_date,
    order_items.order_item_id,
    products.product_id,
    products.product_name,
    products.sku,
    products.active,
    categories.category_id,
    categories.category_name,
    order_items.quantity,
    order_items.sale_price_cents,
    order_items.unit_cost_cents,
    order_items.quantity * order_items.sale_price_cents
        AS recognized_revenue_cents,
    order_items.quantity * order_items.unit_cost_cents
        AS cost_of_goods_cents,
    order_items.quantity
        * (order_items.sale_price_cents - order_items.unit_cost_cents)
        AS gross_margin_cents
FROM orders
JOIN order_items
    ON order_items.order_id = orders.order_id
JOIN products
    ON products.product_id = order_items.product_id
JOIN categories
    ON categories.category_id = products.category_id
WHERE orders.order_status = 'COMPLETED';

CREATE VIEW revenue_by_product AS
SELECT
    product_id,
    product_name,
    category_name,
    ROUND(SUM(recognized_revenue_cents) / 100.0, 2) AS revenue
FROM completed_order_lines
GROUP BY product_id, product_name, category_name;

CREATE VIEW revenue_by_category AS
SELECT
    category_id,
    category_name,
    ROUND(SUM(recognized_revenue_cents) / 100.0, 2) AS revenue
FROM completed_order_lines
GROUP BY category_id, category_name;

CREATE VIEW margin_by_product AS
SELECT
    product_id,
    product_name,
    category_name,
    ROUND(SUM(recognized_revenue_cents) / 100.0, 2) AS revenue,
    ROUND(SUM(cost_of_goods_cents) / 100.0, 2) AS total_cost,
    ROUND(SUM(gross_margin_cents) / 100.0, 2) AS gross_margin,
    CASE
        WHEN SUM(recognized_revenue_cents) > 0
            THEN ROUND(
                SUM(gross_margin_cents)
                * 100.0
                / SUM(recognized_revenue_cents),
                1
            )
        ELSE NULL
    END AS gross_margin_rate
FROM completed_order_lines
GROUP BY product_id, product_name, category_name;

CREATE VIEW product_revenue_rank AS
SELECT
    product_id,
    product_name,
    category_name,
    revenue,
    total_cost,
    gross_margin,
    gross_margin_rate,
    RANK() OVER (ORDER BY revenue DESC) AS revenue_rank
FROM margin_by_product;

CREATE VIEW monthly_performance AS
SELECT
    SUBSTR(order_date, 1, 7) AS month,
    ROUND(SUM(recognized_revenue_cents) / 100.0, 2)
        AS recognized_revenue,
    ROUND(SUM(gross_margin_cents) / 100.0, 2) AS gross_margin,
    COUNT(DISTINCT order_id) AS completed_orders,
    COUNT(*) AS order_lines
FROM completed_order_lines
GROUP BY SUBSTR(order_date, 1, 7)
ORDER BY month;

CREATE VIEW dashboard_summary AS
SELECT
    ROUND(
        COALESCE(SUM(recognized_revenue_cents), 0) / 100.0,
        2
    ) AS recognized_revenue,
    ROUND(COALESCE(SUM(gross_margin_cents), 0) / 100.0, 2)
        AS gross_margin,
    COUNT(DISTINCT order_id) AS completed_orders,
    COUNT(DISTINCT CASE WHEN active = 1 THEN product_id END)
        AS active_products,
    COUNT(*) AS order_lines
FROM completed_order_lines;
