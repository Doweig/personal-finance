---
title: Restaurant Detail
---

<script>
    import PageNav from '../../../components/PageNav.svelte';
</script>

```sql restaurant_info
select name, restaurant_code from portfolio.restaurants where id = '${params.id}'
```

<PageNav active="restaurants" context={restaurant_info[0].name} />

# {restaurant_info[0].name}

```sql monthly_data
select
    pl.month,
    pl.revenue,
    pl.revenue_n1,
    pl.food_cost,
    pl.beverage_cost,
    pl.total_fb_cost,
    pl.total_other_expenses,
    pl.total_monthly_exp,
    pl.gop_before_fee,
    pl.gop_net,
    pl.rebate,
    case when pl.revenue > 0 then pl.gop_net / pl.revenue * 100 end as gop_margin_pct,
    case when pl.revenue > 0 then pl.total_fb_cost / pl.revenue * 100 end as fb_cost_pct,
    avg(pl.revenue) over (
        order by pl.month
        rows between 5 preceding and current row
    ) as revenue_6mma,
    avg(pl.gop_net) over (
        order by pl.month
        rows between 5 preceding and current row
    ) as gop_net_6mma,
    avg(pl.total_monthly_exp) over (
        order by pl.month
        rows between 5 preceding and current row
    ) as total_exp_6mma,
    avg(pl.total_fb_cost) over (
        order by pl.month
        rows between 5 preceding and current row
    ) as fb_cost_6mma,
    avg(case when pl.revenue > 0 then pl.gop_net / pl.revenue * 100 end) over (
        order by pl.month
        rows between 5 preceding and current row
    ) as gop_margin_6mma,
    avg(case when pl.revenue > 0 then pl.total_fb_cost / pl.revenue * 100 end) over (
        order by pl.month
        rows between 5 preceding and current row
    ) as fb_cost_pct_6mma,
    avg(pl.revenue) over (
        order by pl.month
        rows between 11 preceding and current row
    ) as revenue_12sma,
    avg(pl.gop_net) over (
        order by pl.month
        rows between 11 preceding and current row
    ) as gop_net_12sma,
    count(*) over (
        order by pl.month
        rows between 11 preceding and current row
    ) as window_size
from portfolio.monthly_pl pl
where pl.restaurant_id = '${params.id}'
order by pl.month
```

```sql latest_snapshot
select
    month,
    revenue,
    revenue_6mma,
    gop_net,
    gop_net_6mma,
    gop_margin_pct
from ${monthly_data}
order by month desc
limit 1
```

```sql valuations
select
    month,
    case when window_size >= 12 then revenue_12sma * 12 end as revenue_valuation,
    case when window_size >= 12 then gop_net_12sma * 12 * 4 end as income_valuation,
    case when window_size >= 12 then (revenue_12sma * 12 + gop_net_12sma * 12 * 4) / 2 end as blended_valuation
from ${monthly_data}
where window_size >= 12
```

<BigValue data={latest_snapshot} value=revenue title="Latest Revenue (THB)" fmt='#,##0' />
<BigValue data={latest_snapshot} value=revenue_6mma title="Revenue 6M MA (THB)" fmt='#,##0' />
<BigValue data={latest_snapshot} value=gop_net title="Latest GOP Net (THB)" fmt='#,##0' />
<BigValue data={latest_snapshot} value=gop_margin_pct title="Latest GOP Margin %" fmt='0.0"%"' />

## Revenue

<LineChart data={monthly_data} x=month y={["revenue", "revenue_6mma", "revenue_n1"]} title="Revenue (Actual, 6M MA, Prior Year)" yFmt='#,##0' />

## Earnings

<LineChart data={monthly_data} x=month y={["gop_net", "gop_net_6mma"]} title="GOP Net (Actual vs 6M MA)" yFmt='#,##0' />

## Costs

<LineChart data={monthly_data} x=month y={["total_monthly_exp", "total_exp_6mma", "total_fb_cost", "fb_cost_6mma"]} title="Total Expenses and F&B Costs (Actual vs 6M MA)" yFmt='#,##0' />

## Margins

<LineChart data={monthly_data} x=month y={["gop_margin_pct", "gop_margin_6mma", "fb_cost_pct", "fb_cost_pct_6mma"]} title="Margins and Cost Ratios (Actual vs 6M MA)" yFmt='0.0"%"' />

## Valuation

<LineChart data={valuations} x=month y={["revenue_valuation", "income_valuation", "blended_valuation"]} title="Valuation Estimates" yFmt='#,##0' />

## Monthly P&L

<DataTable data={monthly_data} rows=all>
    <Column id=month title="Month" />
    <Column id=revenue title="Revenue" fmt='#,##0' />
    <Column id=revenue_6mma title="Revenue 6M MA" fmt='#,##0' />
    <Column id=revenue_n1 title="Rev N-1" fmt='#,##0' />
    <Column id=food_cost title="Food Cost" fmt='#,##0' />
    <Column id=beverage_cost title="Bev Cost" fmt='#,##0' />
    <Column id=total_fb_cost title="Total F&B" fmt='#,##0' />
    <Column id=fb_cost_pct title="F&B %" fmt='0.0"%"' />
    <Column id=total_other_expenses title="Other Exp" fmt='#,##0' />
    <Column id=total_monthly_exp title="Total Exp" fmt='#,##0' />
    <Column id=gop_before_fee title="GOP Pre-Fee" fmt='#,##0' />
    <Column id=gop_net title="GOP Net" fmt='#,##0' />
    <Column id=gop_net_6mma title="GOP 6M MA" fmt='#,##0' />
    <Column id=gop_margin_pct title="GOP %" fmt='0.0"%"' />
    <Column id=rebate title="Rebate" fmt='#,##0' />
</DataTable>
