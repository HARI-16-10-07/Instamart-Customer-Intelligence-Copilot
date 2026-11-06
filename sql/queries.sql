
-- ============================================================
-- INSTAMART CUSTOMER INTELLIGENCE & SUPPORT COPILOT
-- Database: SQLite
-- Currency: INR
-- ============================================================



-- Find customers whose completed orders above INR 500
-- have a combined amount greater than INR 8,000.

SELECT
    customer_id,
    COUNT(*) AS qualifying_orders,
    ROUND(SUM(order_amount), 2) AS total_spend_inr
FROM orders
WHERE status = 'completed'
  AND order_amount > 500
GROUP BY customer_id
HAVING SUM(order_amount) > 8000
ORDER BY total_spend_inr DESC;



-- Calculate revenue by city and product category.

SELECT
    c.city,
    p.category,
    COUNT(o.order_id) AS completed_orders,
    ROUND(SUM(o.order_amount), 2) AS revenue_inr
FROM orders o
JOIN customers c
    ON o.customer_id = c.customer_id
JOIN products p
    ON o.product_id = p.product_id
WHERE o.status = 'completed'
GROUP BY c.city, p.category
ORDER BY c.city, p.category;



-- Find products priced above the average catalogue price.

SELECT
    product_id,
    product_name,
    category,
    price_inr
FROM products
WHERE price_inr > (
    SELECT AVG(price_inr)
    FROM products
)
ORDER BY price_inr DESC;



-- Find customers who have never placed a completed order.

SELECT
    c.customer_id,
    c.city,
    c.gender
FROM customers c
LEFT JOIN orders o
    ON c.customer_id = o.customer_id
   AND o.status = 'completed'
WHERE o.order_id IS NULL
ORDER BY c.customer_id;



-- Find customers whose completed-order spending
-- is greater than the average customer spending.

WITH customer_spending AS (
    SELECT
        customer_id,
        SUM(order_amount) AS total_spend_inr
    FROM orders
    WHERE status = 'completed'
    GROUP BY customer_id
),
average_spending AS (
    SELECT AVG(total_spend_inr) AS average_spend
    FROM customer_spending
)
SELECT
    cs.customer_id,
    ROUND(cs.total_spend_inr, 2) AS total_spend_inr,
    ROUND(av.average_spend, 2) AS average_spend_inr
FROM customer_spending cs
CROSS JOIN average_spending av
WHERE cs.total_spend_inr > av.average_spend
ORDER BY cs.total_spend_inr DESC;



-- Rank customers within each city by completed spending.
-- Demonstrates RANK, DENSE_RANK and ROW_NUMBER.

WITH customer_city_spending AS (
    SELECT
        c.city,
        c.customer_id,
        ROUND(SUM(o.order_amount), 2) AS total_spend_inr
    FROM customers c
    JOIN orders o
        ON c.customer_id = o.customer_id
    WHERE o.status = 'completed'
    GROUP BY c.city, c.customer_id
)
SELECT
    city,
    customer_id,
    total_spend_inr,

    RANK() OVER (
        PARTITION BY city
        ORDER BY total_spend_inr DESC
    ) AS spending_rank,

    DENSE_RANK() OVER (
        PARTITION BY city
        ORDER BY total_spend_inr DESC
    ) AS dense_spending_rank,

    ROW_NUMBER() OVER (
        PARTITION BY city
        ORDER BY total_spend_inr DESC
    ) AS row_number_rank

FROM customer_city_spending
ORDER BY city, spending_rank, customer_id;


-- Calculate daily completed revenue and cumulative revenue.

WITH daily_revenue AS (
    SELECT
        SUBSTR(order_ts, 1, 10) AS order_date,
        ROUND(SUM(order_amount), 2) AS daily_revenue_inr
    FROM orders
    WHERE status = 'completed'
    GROUP BY SUBSTR(order_ts, 1, 10)
)
SELECT
    order_date,
    daily_revenue_inr,

    ROUND(
        SUM(daily_revenue_inr) OVER (
            ORDER BY order_date
            ROWS BETWEEN UNBOUNDED PRECEDING
            AND CURRENT ROW
        ),
        2
    ) AS cumulative_revenue_inr

FROM daily_revenue
ORDER BY order_date;