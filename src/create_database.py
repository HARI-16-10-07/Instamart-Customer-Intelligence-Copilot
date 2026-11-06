
from pathlib import Path
import sqlite3
import pandas as pd

# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

CLEAN_DIR = BASE_DIR / "data" / "clean"
DB_PATH = BASE_DIR / "data" / "instamart.db"


def create_database():

    # Read the three cleaned CSV files
    customers = pd.read_csv(CLEAN_DIR / "customers.csv")
    products = pd.read_csv(CLEAN_DIR / "products.csv")
    orders = pd.read_csv(CLEAN_DIR / "orders.csv")

    # Connect to SQLite database
    connection = sqlite3.connect(DB_PATH)

    try:
        # Enable foreign key enforcement
        connection.execute("PRAGMA foreign_keys = ON")

        cursor = connection.cursor()

        # Recreate tables so repeated runs are consistent
        cursor.execute("DROP TABLE IF EXISTS orders")
        cursor.execute("DROP TABLE IF EXISTS products")
        cursor.execute("DROP TABLE IF EXISTS customers")

        # --------------------------------------------------
        # CUSTOMERS TABLE
        # --------------------------------------------------

        cursor.execute("""
            CREATE TABLE customers (
                customer_id TEXT PRIMARY KEY,
                city TEXT NOT NULL,
                signup_date TEXT,
                age REAL,
                gender TEXT NOT NULL
                    CHECK (gender IN ('male', 'female', 'unknown'))
            )
        """)

        # --------------------------------------------------
        # PRODUCTS TABLE
        # --------------------------------------------------

        cursor.execute("""
            CREATE TABLE products (
                product_id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                category TEXT NOT NULL,
                price_inr REAL NOT NULL
                    CHECK (price_inr >= 0)
            )
        """)

        # --------------------------------------------------
        # ORDERS TABLE
        # --------------------------------------------------

        cursor.execute("""
            CREATE TABLE orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                quantity INTEGER NOT NULL
                    CHECK (quantity > 0),
                order_ts TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK (status IN ('completed', 'cancelled')),
                discount_pct REAL,
                order_amount REAL NOT NULL
                    CHECK (order_amount >= 0),
                delivery_minutes REAL,

                FOREIGN KEY (customer_id)
                    REFERENCES customers(customer_id),

                FOREIGN KEY (product_id)
                    REFERENCES products(product_id)
            )
        """)

        # --------------------------------------------------
        # INSERT CLEANED DATA
        # --------------------------------------------------

        customers.to_sql(
            "customers",
            connection,
            if_exists="append",
            index=False
        )

        products.to_sql(
            "products",
            connection,
            if_exists="append",
            index=False
        )

        orders.to_sql(
            "orders",
            connection,
            if_exists="append",
            index=False
        )

        connection.commit()

        # --------------------------------------------------
        # DATABASE VALIDATION
        # --------------------------------------------------

        print("=" * 65)
        print("INSTAMART SQLITE DATABASE VALIDATION")
        print("=" * 65)

        for table in ["customers", "products", "orders"]:

            count = pd.read_sql_query(
                f"SELECT COUNT(*) AS total FROM {table}",
                connection
            )["total"][0]

            print(f"{table}: {count} rows")

        # Verify foreign key relationships
        foreign_key_errors = cursor.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        print("\nForeign key errors:", len(foreign_key_errors))

        # Display database table names
        table_names = cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
        """).fetchall()

        print("\nDatabase tables:")
        for table in table_names:
            print("-", table[0])

        # Reference assertions
        assert len(customers) == 1200
        assert len(products) == 40
        assert len(orders) == 12309

        assert len(foreign_key_errors) == 0

        assert len(table_names) == 3

        print("\nALL DATABASE CHECKPOINTS PASSED")
        print("\nDatabase saved at:", DB_PATH)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    create_database()
