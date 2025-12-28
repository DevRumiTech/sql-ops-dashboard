Retail Operations & Margin Analytics Dashboard

This project demonstrates strong, practical SQL skills through the design of a realistic retail analytics system. It models customers, orders, products, categories, suppliers, and inventory using a normalized relational database, with business rules enforced directly in SQL.

The project focuses on using SQL as the core of the application. Reporting logic is implemented through SQL views that calculate revenue by product, gross margin, revenue by category, and product rankings using joins, aggregations, and window functions. These views are exposed through a lightweight backend and rendered in a simple web interface so results are immediately visible.

The database schema enforces data integrity using primary keys, foreign keys, uniqueness constraints, and check constraints. Inventory is modeled using movement events rather than a static stock column, allowing accurate tracking of restocks, sales, and adjustments over time. Monetary values are stored as integer cents to avoid floating-point errors.

This project reflects how SQL is used in real internal tools and analytics systems rather than academic or toy examples. The emphasis is on clear schema design, meaningful queries, and practical business reporting.

Technology stack: SQLite, Python (Flask), HTML, CSS, JavaScript.