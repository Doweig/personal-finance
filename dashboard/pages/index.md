---
title: Portfolio Overview
---

```sql kpi_invested
select sum(amount_thb) as total_invested
from portfolio.investments
```

```sql kpi_dividends
select sum(my_share_thb) as total_dividends
from portfolio.dividends
```

```sql latest_valuations
with monthly_window as (
    select
        restaurant_id,
        month,
        avg(revenue) over (
            partition by restaurant_id
            order by month
            rows between 11 preceding and current row
        ) as revenue_12sma,
        avg(gop_net) over (
            partition by restaurant_id
            order by month
            rows between 11 preceding and current row
        ) as gop_net_12sma,
        count(*) over (
            partition by restaurant_id
            order by month
            rows between 11 preceding and current row
        ) as window_size
    from portfolio.monthly_pl
),
latest as (
    select
        restaurant_id,
        month,
        revenue_12sma,
        gop_net_12sma,
        revenue_12sma * 12 as revenue_valuation,
        gop_net_12sma * 12 * 4 as income_valuation,
        (revenue_12sma * 12 + gop_net_12sma * 12 * 4) / 2.0 as blended_valuation
    from monthly_window
    where window_size >= 12
    qualify row_number() over (partition by restaurant_id order by month desc) = 1
)
select * from latest
```

```sql latest_ownership
select
    restaurant_id,
    ownership_pct
from portfolio.ownership
qualify row_number() over (partition by restaurant_id order by effective_date desc) = 1
```

```sql kpi_valuation
select sum(v.blended_valuation * o.ownership_pct / 100.0) as portfolio_valuation
from ${latest_valuations} v
join ${latest_ownership} o on v.restaurant_id = o.restaurant_id
```

```sql restaurant_summary
select
    r.id,
    r.name,
    '/restaurants/' || r.id as link_col,
    o.ownership_pct,
    coalesce(i.invested, 0) as invested,
    coalesce(v.blended_valuation * o.ownership_pct / 100.0, 0) as my_valuation,
    coalesce(d.total_dividends, 0) as total_dividends,
    v.month as latest_month
from portfolio.restaurants r
left join ${latest_ownership} o on r.id = o.restaurant_id
left join (
    select restaurant_id, sum(amount_thb) as invested
    from portfolio.investments
    group by restaurant_id
) i on r.id = i.restaurant_id
left join ${latest_valuations} v on r.id = v.restaurant_id
left join (
    select restaurant_id, sum(my_share_thb) as total_dividends
    from portfolio.dividends
    group by restaurant_id
) d on r.id = d.restaurant_id
order by r.name
```

<BigValue data={kpi_invested} value=total_invested title="Total Invested (THB)" fmt='#,##0' />

<BigValue data={kpi_valuation} value=portfolio_valuation title="Portfolio Valuation - My Share (THB)" fmt='#,##0' />

<BigValue data={kpi_dividends} value=total_dividends title="Total Dividends (THB)" fmt='#,##0' />

<DataTable data={restaurant_summary} link=link_col>
    <Column id=name title="Restaurant" />
    <Column id=ownership_pct title="Ownership %" fmt='0.0"%"' />
    <Column id=invested title="Invested (THB)" fmt='#,##0' />
    <Column id=my_valuation title="Valuation - My Share (THB)" fmt='#,##0' />
    <Column id=total_dividends title="Total Dividends (THB)" fmt='#,##0' />
    <Column id=latest_month title="Latest Month" />
</DataTable>
