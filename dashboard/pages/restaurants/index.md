---
title: Restaurants
---

<script>
    import PageNav from '../../components/PageNav.svelte';
</script>

<PageNav active="restaurants" />

## Restaurant Performance

```sql latest_monthly
with trends as (
    select
        pl.restaurant_id,
        pl.month,
        pl.revenue,
        pl.gop_net,
        avg(pl.revenue) over (
            partition by pl.restaurant_id
            order by pl.month
            rows between 5 preceding and current row
        ) as revenue_6mma,
        avg(pl.gop_net) over (
            partition by pl.restaurant_id
            order by pl.month
            rows between 5 preceding and current row
        ) as gop_6mma
    from portfolio.monthly_pl pl
)
select
    restaurant_id,
    month,
    revenue,
    gop_net,
    revenue_6mma,
    gop_6mma
from trends
qualify row_number() over (partition by restaurant_id order by month desc) = 1
```

```sql summary
select
    r.id,
    r.name,
    '/restaurants/' || r.id as link_col,
    case
        when coalesce(lm.month, inv.invested_since) is null then ''
        else strftime(coalesce(lm.month, inv.invested_since), '%Y-%m')
    end as latest_month,
    coalesce(inv.total_invested, 0) as invested,
    coalesce(divs.total_dividends, 0) as dividends,
    lm.revenue,
    lm.revenue_6mma,
    lm.gop_net,
    lm.gop_6mma
from portfolio.restaurants r
left join ${latest_monthly} lm on r.id = lm.restaurant_id
left join (
    select restaurant_id, sum(amount_thb) as total_invested, min(date) as invested_since
    from portfolio.investments
    group by restaurant_id
) inv on r.id = inv.restaurant_id
left join (
    select restaurant_id, sum(my_share_thb) as total_dividends
    from portfolio.dividends
    group by restaurant_id
) divs on r.id = divs.restaurant_id
order by r.name
```

```sql revenue_trend
select
    pl.month,
    r.name as restaurant_name,
    avg(pl.revenue) over (
        partition by pl.restaurant_id
        order by pl.month
        rows between 5 preceding and current row
    ) as revenue_6mma
from portfolio.monthly_pl pl
join portfolio.restaurants r on pl.restaurant_id = r.id
order by pl.month
```

```sql gop_trend
select
    pl.month,
    r.name as restaurant_name,
    avg(pl.gop_net) over (
        partition by pl.restaurant_id
        order by pl.month
        rows between 5 preceding and current row
    ) as gop_6mma
from portfolio.monthly_pl pl
join portfolio.restaurants r on pl.restaurant_id = r.id
order by pl.month
```

<DataTable data={summary} link=link_col>
    <Column id=name title="Restaurant" />
    <Column id=latest_month title="Latest Month" />
    <Column id=invested title="Invested (THB)" fmt='#,##0' />
    <Column id=dividends title="Dividends (THB)" fmt='#,##0' />
    <Column id=revenue title="Latest Revenue (THB)" fmt='#,##0' />
    <Column id=revenue_6mma title="Revenue 6M MA (THB)" fmt='#,##0' />
    <Column id=gop_net title="Latest GOP (THB)" fmt='#,##0' />
    <Column id=gop_6mma title="GOP 6M MA (THB)" fmt='#,##0' />
</DataTable>

## Revenue Trend (6M MA)

<LineChart data={revenue_trend} x=month y=revenue_6mma series=restaurant_name yFmt='#,##0' />

## GOP Trend (6M MA)

<LineChart data={gop_trend} x=month y=gop_6mma series=restaurant_name yFmt='#,##0' />
