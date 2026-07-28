PRAGMA foreign_keys = ON;

CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY,
    category_name TEXT NOT NULL UNIQUE
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL UNIQUE,
    category_id INTEGER NOT NULL,
    unit_cost_cents INTEGER NOT NULL CHECK (unit_cost_cents >= 0),
    list_price_cents INTEGER NOT NULL
        CHECK (list_price_cents >= unit_cost_cents),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    order_date TEXT NOT NULL
        CHECK (
            length(order_date) = 10
            AND date(order_date) = order_date
        ),
    order_status TEXT NOT NULL
        CHECK (order_status IN ('COMPLETED', 'PENDING', 'CANCELLED')),
    sales_channel TEXT NOT NULL
        CHECK (sales_channel IN ('ONLINE', 'STORE', 'PARTNER'))
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    sale_price_cents INTEGER NOT NULL CHECK (sale_price_cents >= 0),
    unit_cost_cents INTEGER NOT NULL CHECK (unit_cost_cents >= 0),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Dashboard analytics always filter completed orders by date.
CREATE INDEX idx_orders_status_date
    ON orders (order_status, order_date);

-- SQLite does not automatically index foreign-key columns.
CREATE INDEX idx_order_items_order_id
    ON order_items (order_id);

CREATE INDEX idx_order_items_product_id
    ON order_items (product_id);

-- Category and active-product filters use this product lookup.
CREATE INDEX idx_products_category_active
    ON products (category_id, active);
