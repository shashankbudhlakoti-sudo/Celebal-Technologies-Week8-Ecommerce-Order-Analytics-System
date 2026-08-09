-- =====================================================================
-- PHASE 1 - Part 3: SQL Analysis
-- Database: data/ecommerce.db (SQLite)
-- Revenue formula used throughout: quantity * unit_price * (1 - discount_percent/100)
--   -> pre-computed as order_items.revenue during Part 2 cleaning.
--   -> NOTE: quantity is signed (negative = RETURN), so revenue naturally
--      nets out returns wherever it's summed, matching the assignment's formula.
-- =====================================================================


-- =====================================================================
-- BASIC QUERIES
-- =====================================================================

-- 1. Total revenue per category
SELECT
    p.category,
    ROUND(SUM(oi.revenue), 2) AS total_revenue
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY total_revenue DESC;


-- 2. Top 10 customers by total order value
SELECT
    c.customer_id,
    c.customer_name,
    ROUND(SUM(oi.revenue), 2) AS total_order_value
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
GROUP BY c.customer_id, c.customer_name
ORDER BY total_order_value DESC
LIMIT 10;


-- 3. Month-wise order count for the last 12 months
--    ("last 12 months" is relative to the most recent order_date in the dataset,
--     since this is a static synthetic dataset rather than a live feed.)
SELECT
    strftime('%Y-%m', order_date) AS year_month,
    COUNT(*) AS order_count
FROM orders
WHERE order_date >= date((SELECT MAX(order_date) FROM orders), '-12 months')
GROUP BY year_month
ORDER BY year_month;


-- =====================================================================
-- INTERMEDIATE QUERIES
-- =====================================================================

-- 4. Customers who placed orders but never had any order delivered
SELECT
    c.customer_id,
    c.customer_name,
    COUNT(o.order_id) AS total_orders
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
HAVING SUM(CASE WHEN o.status = 'DELIVERED' THEN 1 ELSE 0 END) = 0
ORDER BY total_orders DESC;


-- 5. Products that were ordered but had more returns than purchases
SELECT
    p.product_id,
    p.product_name,
    SUM(CASE WHEN oi.transaction_type = 'PURCHASE' THEN oi.quantity_abs ELSE 0 END) AS purchase_qty,
    SUM(CASE WHEN oi.transaction_type = 'RETURN'   THEN oi.quantity_abs ELSE 0 END) AS return_qty
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.product_id, p.product_name
HAVING return_qty > purchase_qty
ORDER BY return_qty DESC;


-- 6. Return rate (returned items / total items) per category
SELECT
    p.category,
    SUM(oi.quantity_abs) AS total_items,
    SUM(CASE WHEN oi.transaction_type = 'RETURN' THEN oi.quantity_abs ELSE 0 END) AS returned_items,
    ROUND(
        SUM(CASE WHEN oi.transaction_type = 'RETURN' THEN oi.quantity_abs ELSE 0 END) * 100.0
        / SUM(oi.quantity_abs), 2
    ) AS return_rate_percent
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY return_rate_percent DESC;


-- =====================================================================
-- ADVANCED QUERIES (Window Functions, CTEs, Subqueries)
-- =====================================================================

-- 7. Running Totals with Window Functions
--    Running total of revenue per region, ordered by date.
WITH daily AS (
    SELECT
        o.region_code,
        date(o.order_date) AS order_date,
        SUM(oi.revenue) AS daily_revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    GROUP BY o.region_code, date(o.order_date)
)
SELECT
    region_code,
    order_date,
    ROUND(daily_revenue, 2) AS daily_revenue,
    ROUND(SUM(daily_revenue) OVER (
        PARTITION BY region_code ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2) AS running_total
FROM daily
ORDER BY region_code, order_date;


-- 8. Ranking with DENSE_RANK
--    Rank products by total revenue within each category (ties share the same rank).
WITH prod_rev AS (
    SELECT
        p.category,
        p.product_name,
        SUM(oi.revenue) AS total_revenue
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
    GROUP BY p.category, p.product_name
)
SELECT
    category,
    product_name,
    ROUND(total_revenue, 2) AS total_revenue,
    DENSE_RANK() OVER (PARTITION BY category ORDER BY total_revenue DESC) AS rank_in_category
FROM prod_rev
ORDER BY category, rank_in_category;


-- 9. LAG/LEAD Analysis
--    Days between consecutive orders per customer; flag "At Risk" if avg gap > 30 days.
WITH cust_orders AS (
    SELECT
        customer_id,
        order_date,
        LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS previous_order_date
    FROM orders
    WHERE customer_id <> 'UNKNOWN'
),
gaps AS (
    SELECT
        customer_id,
        order_date,
        previous_order_date,
        CASE WHEN previous_order_date IS NOT NULL
             THEN julianday(order_date) - julianday(previous_order_date)
        END AS days_gap
    FROM cust_orders
)
SELECT
    customer_id,
    order_date,
    previous_order_date,
    ROUND(days_gap, 1) AS days_gap,
    CASE WHEN AVG(days_gap) OVER (PARTITION BY customer_id) > 30 THEN 'At Risk' ELSE 'Active' END AS risk_status
FROM gaps
ORDER BY customer_id, order_date;


-- 10. CTE with Multiple Levels
--     Monthly revenue per customer -> categorize High/Medium/Low -> count customers per category per month.
WITH monthly_rev AS (
    SELECT
        o.customer_id,
        strftime('%Y-%m', o.order_date) AS year_month,
        SUM(oi.revenue) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id <> 'UNKNOWN'
    GROUP BY o.customer_id, year_month
),
categorized AS (
    SELECT
        year_month,
        customer_id,
        revenue,
        CASE
            WHEN revenue > 10000 THEN 'High'
            WHEN revenue >= 5000 THEN 'Medium'
            ELSE 'Low'
        END AS revenue_category
    FROM monthly_rev
)
SELECT
    year_month,
    revenue_category,
    COUNT(DISTINCT customer_id) AS customer_count
FROM categorized
GROUP BY year_month, revenue_category
ORDER BY year_month, revenue_category;


-- 11. NTILE for Segmentation
--     Divide customers into 4 quartiles by total lifetime value.
WITH cust_value AS (
    SELECT
        o.customer_id,
        SUM(oi.revenue) AS total_value
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id <> 'UNKNOWN'
    GROUP BY o.customer_id
),
ranked AS (
    SELECT
        customer_id,
        total_value,
        NTILE(4) OVER (ORDER BY total_value DESC) AS quartile
    FROM cust_value
)
SELECT
    customer_id,
    ROUND(total_value, 2) AS total_value,
    quartile,
    CASE quartile
        WHEN 1 THEN 'Platinum'
        WHEN 2 THEN 'Gold'
        WHEN 3 THEN 'Silver'
        WHEN 4 THEN 'Bronze'
    END AS quartile_label
FROM ranked
ORDER BY total_value DESC;


-- 12. Year-over-Year Comparison
--     Compare each month's revenue with the same month in the previous year.
WITH monthly AS (
    SELECT
        strftime('%Y', o.order_date) AS year,
        strftime('%m', o.order_date) AS month,
        SUM(oi.revenue) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    GROUP BY year, month
)
SELECT
    cur.year,
    cur.month,
    ROUND(cur.revenue, 2) AS revenue,
    ROUND(prev.revenue, 2) AS prev_year_revenue,
    CASE
        WHEN prev.revenue IS NOT NULL AND prev.revenue <> 0
        THEN ROUND((cur.revenue - prev.revenue) * 100.0 / prev.revenue, 2)
        ELSE NULL   -- no prior-year data available
    END AS yoy_growth_percent
FROM monthly cur
LEFT JOIN monthly prev
    ON prev.month = cur.month
    AND CAST(prev.year AS INTEGER) = CAST(cur.year AS INTEGER) - 1
ORDER BY cur.year, cur.month;


-- 13. First/Last Value Analysis
--     Each customer's first purchased category vs. most recent purchased category.
WITH cust_cat AS (
    SELECT
        o.customer_id,
        o.order_date,
        p.category,
        FIRST_VALUE(p.category) OVER (
            PARTITION BY o.customer_id ORDER BY o.order_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS first_category,
        LAST_VALUE(p.category) OVER (
            PARTITION BY o.customer_id ORDER BY o.order_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS last_category
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    JOIN products p ON p.product_id = oi.product_id
    WHERE o.customer_id <> 'UNKNOWN'
)
SELECT DISTINCT
    customer_id,
    first_category,
    last_category,
    CASE WHEN first_category <> last_category THEN 'Yes' ELSE 'No' END AS category_shift
FROM cust_cat
ORDER BY customer_id;


-- 14. Cumulative Distribution
--     What % of total revenue comes from the top N% of customers.
WITH cust_rev AS (
    SELECT
        o.customer_id,
        SUM(oi.revenue) AS revenue
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.customer_id <> 'UNKNOWN'
    GROUP BY o.customer_id
),
ranked AS (
    SELECT
        customer_id,
        revenue,
        SUM(revenue) OVER (ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_revenue,
        SUM(revenue) OVER () AS total_revenue
    FROM cust_rev
)
SELECT
    customer_id,
    ROUND(revenue, 2) AS revenue,
    ROUND(cumulative_revenue, 2) AS cumulative_revenue,
    ROUND(cumulative_revenue * 100.0 / total_revenue, 2) AS cumulative_percent
FROM ranked
ORDER BY revenue DESC;


-- 15. Complex CTE: Cohort Analysis
--     Group customers by registration month; track how many ordered in month 0/1/2/3, with retention rate.
WITH cohorts AS (
    SELECT
        customer_id,
        strftime('%Y-%m', registration_date) AS cohort_month
    FROM customers
),
cust_orders AS (
    SELECT
        o.customer_id,
        c.cohort_month,
        (CAST(strftime('%Y', o.order_date) AS INTEGER) * 12 + CAST(strftime('%m', o.order_date) AS INTEGER))
      - (CAST(substr(c.cohort_month, 1, 4) AS INTEGER) * 12 + CAST(substr(c.cohort_month, 6, 2) AS INTEGER)) AS month_number
    FROM orders o
    JOIN cohorts c ON c.customer_id = o.customer_id
    WHERE o.customer_id <> 'UNKNOWN'
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
),
activity AS (
    SELECT
        cohort_month,
        month_number,
        COUNT(DISTINCT customer_id) AS active_customers
    FROM cust_orders
    WHERE month_number BETWEEN 0 AND 3
    GROUP BY cohort_month, month_number
)
SELECT
    a.cohort_month,
    a.month_number,
    a.active_customers,
    cs.cohort_size,
    ROUND(a.active_customers * 100.0 / cs.cohort_size, 2) AS retention_rate_percent
FROM activity a
JOIN cohort_sizes cs ON cs.cohort_month = a.cohort_month
ORDER BY a.cohort_month, a.month_number;


-- 16. Self-Join with Window Function
--     For each customer order, find their NEXT order via a self-join keyed on
--     ROW_NUMBER() (an alternative technique to LAG/LEAD used in Q9).
WITH numbered AS (
    SELECT
        order_id,
        customer_id,
        order_date,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date) AS rn
    FROM orders
    WHERE customer_id <> 'UNKNOWN'
)
SELECT
    a.customer_id,
    a.order_id AS current_order_id,
    a.order_date AS current_order_date,
    b.order_id AS next_order_id,
    b.order_date AS next_order_date,
    ROUND(julianday(b.order_date) - julianday(a.order_date), 1) AS days_until_next_order
FROM numbered a
LEFT JOIN numbered b
    ON a.customer_id = b.customer_id AND b.rn = a.rn + 1
ORDER BY a.customer_id, a.order_date;
