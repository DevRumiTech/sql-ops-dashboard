BEGIN;

-- Small deterministic reference catalogue. Transaction records are generated
-- by scripts/generate_demo_data.py with no personal or contact information.
INSERT INTO categories (category_id, category_name) VALUES
    (1, 'Office'),
    (2, 'Kitchen'),
    (3, 'Fitness'),
    (4, 'Audio'),
    (5, 'Home Technology');

INSERT INTO products (
    product_id,
    sku,
    product_name,
    category_id,
    unit_cost_cents,
    list_price_cents,
    active
) VALUES
    (1, 'OFF-101', 'Standing Desk Pro', 1, 41000, 69900, 1),
    (2, 'OFF-102', 'Ergonomic Task Chair', 1, 27000, 45900, 1),
    (3, 'OFF-103', 'Monitor Arm Duo', 1, 9800, 18900, 1),
    (4, 'OFF-104', 'Mechanical Keyboard', 1, 7200, 13900, 1),
    (5, 'KIT-201', 'Espresso Maker', 2, 19800, 34900, 1),
    (6, 'KIT-202', 'Precision Kettle', 2, 6300, 12900, 1),
    (7, 'KIT-203', 'Countertop Blender', 2, 11200, 21900, 1),
    (8, 'KIT-204', 'Air Fryer XL', 2, 13500, 24900, 1),
    (9, 'FIT-301', 'Yoga Mat Pro', 3, 3500, 9000, 1),
    (10, 'FIT-302', 'Adjustable Dumbbells', 3, 19500, 32900, 1),
    (11, 'FIT-303', 'Recovery Massage Gun', 3, 9200, 17900, 1),
    (12, 'FIT-304', 'Fitness Tracker Band', 3, 5600, 11900, 1),
    (13, 'AUD-401', 'Wireless Earbuds', 4, 6800, 15900, 1),
    (14, 'AUD-402', 'Studio Headphones', 4, 11700, 24900, 1),
    (15, 'AUD-403', 'Portable Speaker', 4, 5800, 12900, 0),
    (16, 'AUD-404', 'USB Podcast Microphone', 4, 8500, 18900, 1),
    (17, 'HOM-501', 'Smart Floor Lamp', 5, 6500, 14900, 1),
    (18, 'HOM-502', 'Air Quality Monitor', 5, 9400, 19900, 1),
    (19, 'HOM-503', 'Robot Vacuum', 5, 23500, 39900, 1),
    (20, 'HOM-504', 'Compact Projector', 5, 30500, 52900, 0);

COMMIT;
