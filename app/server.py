from flask import Flask, request
from app.db import get_conn

# -------------------------------------------------
# App setup (MUST come before routes)
# -------------------------------------------------
app = Flask(__name__)

HTML_PATH = __file__.replace("server.py", "templates.html")
CSS_PATH = __file__.replace("server.py", "styles.css")

# -------------------------------------------------
# SQL helper (SQL-first, no ORM)
# -------------------------------------------------
def run_query(sql, params=None):
    conn = get_conn()
    try:
        cur = conn.execute(sql, params or [])
        rows = [dict(row) for row in cur.fetchall()]
        return rows
    finally:
        conn.close()

# -------------------------------------------------
# Frontend routes
# -------------------------------------------------
@app.get("/")
def home():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    return html

@app.get("/styles.css")
def styles():
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        css = f.read()
    return app.response_class(css, mimetype="text/css")

@app.get("/query")
def query():
    metric = request.args.get("metric", "ping")
    if metric != "ping":
        return {"error": "Unknown metric"}, 400
    return {"ok": True, "message": "Server is up. Next step: database + schema."}

# -------------------------------------------------
# Analytics API routes (backed by SQL views)
# -------------------------------------------------
@app.get("/api/revenue/products")
def revenue_by_product_api():
    sql = """
        SELECT
            product_name,
            revenue
        FROM revenue_by_product
        ORDER BY revenue DESC;
    """
    return run_query(sql)

# -------------------------------------------------
# Entry point
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
