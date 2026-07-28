BEGIN;

-- All names, email addresses, and transactions below are generated
-- demonstration data. Reserved example domains prevent accidental contact.
INSERT INTO customers (customer_id, email, full_name, created_at) VALUES
    (1, 'alex.morgan@example.com', 'Alex Morgan', '2025-12-27 21:02:02'),
    (2, 'jamie.lee@example.com', 'Jamie Lee', '2025-12-27 21:02:02'),
    (3, 'sam.taylor@example.com', 'Sam Taylor', '2025-12-27 21:02:02');

INSERT INTO suppliers (
    supplier_id,
    supplier_name,
    contact_email,
    active
) VALUES
    (1, 'Nova Distribution', 'ops@nova-distribution.example', 1),
    (2, 'Peak Supply Co', 'support@peak-supply.example', 1),
    (3, 'Urban Goods Ltd', 'sales@urban-goods.example', 1);

INSERT INTO categories (category_id, category_name) VALUES
    (1, 'Electronics'),
    (2, 'Home & Kitchen'),
    (3, 'Fitness'),
    (4, 'Office');

INSERT INTO products (
    product_id,
    product_name,
    category_id,
    supplier_id,
    cost_cents,
    price_cents,
    active
) VALUES
    (1, 'Wireless Earbuds', 1, 1, 4200, 7900, 1),
    (2, 'Espresso Maker', 2, 3, 6500, 12900, 1),
    (3, 'Yoga Mat Pro', 3, 2, 1800, 4500, 1),
    (4, 'Standing Desk', 4, 3, 12000, 24900, 1);

INSERT INTO inventory_movements (
    movement_id,
    product_id,
    quantity,
    movement_type,
    movement_at
) VALUES
    (1, 1, 50, 'IN', '2025-12-27 21:03:17'),
    (2, 2, 30, 'IN', '2025-12-27 21:03:17'),
    (3, 3, 100, 'IN', '2025-12-27 21:03:17'),
    (4, 4, 20, 'IN', '2025-12-27 21:03:17'),
    (5, 1, -1, 'OUT', '2025-12-27 21:03:17'),
    (6, 3, -2, 'OUT', '2025-12-27 21:03:17'),
    (7, 2, -1, 'OUT', '2025-12-27 21:03:17'),
    (8, 4, -1, 'OUT', '2025-12-27 21:03:17');

INSERT INTO orders (
    order_id,
    customer_id,
    order_date,
    order_status
) VALUES
    (1, 1, '2025-12-01', 'PAID'),
    (2, 2, '2025-12-02', 'SHIPPED'),
    (3, 3, '2025-12-05', 'PAID');

INSERT INTO order_items (
    order_item_id,
    order_id,
    product_id,
    quantity,
    sale_price_cents
) VALUES
    (1, 1, 1, 1, 7900),
    (2, 1, 3, 2, 4500),
    (3, 2, 2, 1, 12900),
    (4, 3, 4, 1, 24900);

COMMIT;
