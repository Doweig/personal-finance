---
title: Home
---

<script>
    import PageNav from '../components/PageNav.svelte';
</script>

<PageNav active="home" />

## Portfolio Snapshot

```sql kpi_invested
select coalesce(sum(amount_thb), 0) as total_invested
from portfolio.investments
```

```sql kpi_dividends
select coalesce(sum(my_share_thb), 0) as total_dividends
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
select
    coalesce(
        sum(
            case
                when v.blended_valuation is not null and o.ownership_pct is not null
                    then v.blended_valuation * o.ownership_pct / 100.0
                else coalesce(fi.invested, 0)
            end
        ),
        0
    ) as portfolio_valuation
from portfolio.restaurants r
left join ${latest_valuations} v on r.id = v.restaurant_id
left join ${latest_ownership} o on r.id = o.restaurant_id
left join ${first_investment} fi on r.id = fi.restaurant_id
```

```sql latest_month_by_restaurant
select restaurant_id, max(month) as latest_month
from portfolio.monthly_pl
group by restaurant_id
```

```sql first_investment
select restaurant_id, min(date) as invested_since, sum(amount_thb) as invested
from portfolio.investments
group by restaurant_id
```

```sql restaurant_snapshot
select
    r.id,
    r.name,
    '/restaurants/' || r.id as link_col,
    o.ownership_pct,
    coalesce(fi.invested, 0) as invested,
    case
        when v.blended_valuation is not null and o.ownership_pct is not null
            then v.blended_valuation * o.ownership_pct / 100.0
        else coalesce(fi.invested, 0)
    end as my_valuation,
    coalesce(d.total_dividends, 0) as total_dividends,
    case
        when coalesce(lm.latest_month, fi.invested_since) is null then ''
        else strftime(coalesce(lm.latest_month, fi.invested_since), '%Y-%m')
    end as latest_month
from portfolio.restaurants r
left join ${latest_ownership} o on r.id = o.restaurant_id
left join ${latest_valuations} v on r.id = v.restaurant_id
left join ${latest_month_by_restaurant} lm on r.id = lm.restaurant_id
left join ${first_investment} fi on r.id = fi.restaurant_id
left join (
    select restaurant_id, sum(my_share_thb) as total_dividends
    from portfolio.dividends
    group by restaurant_id
) d on r.id = d.restaurant_id
order by r.name
```

<BigValue data={kpi_invested} value=total_invested title="Total Invested (THB)" fmt='#,##0' />
<BigValue data={kpi_valuation} value=portfolio_valuation title="Estimated Value - My Share (THB)" fmt='#,##0' />
<BigValue data={kpi_dividends} value=total_dividends title="Total Dividends Received (THB)" fmt='#,##0' />

## Restaurants At A Glance

<DataTable data={restaurant_snapshot} link=link_col>
    <Column id=name title="Restaurant" />
    <Column id=ownership_pct title="Ownership %" fmt='0.0"%"' />
    <Column id=invested title="Invested (THB)" fmt='#,##0' />
    <Column id=my_valuation title="Valuation - My Share (THB)" fmt='#,##0' />
    <Column id=total_dividends title="Dividends (THB)" fmt='#,##0' />
    <Column id=latest_month title="Latest Data Month" />
</DataTable>
