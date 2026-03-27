---
title: Returns
---

<script>
    import PageNav from '../../components/PageNav.svelte';
    import IRRCalculator from '../../components/IRRCalculator.svelte';

    const now = new Date();

    function monthsAgo(dateStr) {
        const d = new Date(dateStr);
        return (now.getFullYear() - d.getFullYear()) * 12 + (now.getMonth() - d.getMonth());
    }

    $: grouped = (() => {
        const map = {};
        if (cashflows_for_irr && cashflows_for_irr.length > 0) {
            for (const row of cashflows_for_irr) {
                const name = row.restaurant_name;
                if (!map[name]) map[name] = [];
                map[name].push({
                    months_ago: monthsAgo(row.date),
                    amount: row.amount
                });
            }
        }
        return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]));
    })();
</script>

<PageNav active="returns" />

```sql dividend_history
select
    d.date,
    r.name as restaurant_name,
    d.total_thb,
    d.my_share_thb,
    d.comment,
    sum(d.my_share_thb) over (
        partition by d.restaurant_id
        order by d.date
        rows between unbounded preceding and current row
    ) as cumulative_dividends
from portfolio.dividends d
join portfolio.restaurants r on d.restaurant_id = r.id
where d.my_share_thb > 0
order by d.date desc
```

```sql cumulative_by_restaurant
select
    d.date,
    r.name as restaurant_name,
    sum(d.my_share_thb) over (
        partition by d.restaurant_id
        order by d.date
        rows between unbounded preceding and current row
    ) as cumulative_dividends
from portfolio.dividends d
join portfolio.restaurants r on d.restaurant_id = r.id
where d.my_share_thb > 0
order by d.date
```

```sql roi_summary
select
    r.name,
    i.total_invested,
    coalesce(d.total_dividends, 0) as total_dividends,
    case when i.total_invested > 0
        then coalesce(d.total_dividends, 0) / i.total_invested * 100
        else 0
    end as roi_pct,
    i.invested_since,
    case when coalesce(d.avg_monthly_dividend, 0) > 0
        then i.total_invested / d.avg_monthly_dividend
        else null
    end as months_to_roi
from portfolio.restaurants r
join (
    select
        restaurant_id,
        sum(amount_thb) as total_invested,
        min(date) as invested_since
    from portfolio.investments
    group by restaurant_id
) i on r.id = i.restaurant_id
left join (
    select
        restaurant_id,
        sum(my_share_thb) as total_dividends,
        case when count(distinct strftime(date, '%Y-%m')) > 0
            then sum(my_share_thb) / count(distinct strftime(date, '%Y-%m'))
            else 0
        end as avg_monthly_dividend
    from portfolio.dividends
    where my_share_thb > 0
    group by restaurant_id
) d on r.id = d.restaurant_id
order by roi_pct desc
```

```sql cashflows_for_irr
select
    r.name as restaurant_name,
    i.date,
    -i.amount_thb as amount
from portfolio.investments i
join portfolio.restaurants r on i.restaurant_id = r.id

union all

select
    r.name as restaurant_name,
    d.date,
    d.my_share_thb as amount
from portfolio.dividends d
join portfolio.restaurants r on d.restaurant_id = r.id
where d.my_share_thb > 0

order by restaurant_name, date
```

## ROI Summary

<DataTable data={roi_summary}>
    <Column id=name title="Restaurant" />
    <Column id=total_invested title="Invested (THB)" fmt='#,##0' />
    <Column id=total_dividends title="Dividends (THB)" fmt='#,##0' />
    <Column id=roi_pct title="ROI %" fmt='0.1"%"' />
    <Column id=invested_since title="Since" />
    <Column id=months_to_roi title="Months to ROI" fmt='0.0' />
</DataTable>

## Cumulative Dividends

<LineChart data={cumulative_by_restaurant} x=date y=cumulative_dividends series=restaurant_name yFmt='#,##0' title="Cumulative Dividends by Restaurant" />

## Internal Rate of Return (IRR)

{#each grouped as [name, cfs]}
<div style="margin-bottom: 1.5rem;">
    <h4>{name}</h4>
    <IRRCalculator cashflows={cfs} />
</div>
{/each}

## Dividend History

<DataTable data={dividend_history} rows=all>
    <Column id=date title="Date" />
    <Column id=restaurant_name title="Restaurant" />
    <Column id=total_thb title="Total (THB)" fmt='#,##0' />
    <Column id=my_share_thb title="My Share (THB)" fmt='#,##0' />
    <Column id=cumulative_dividends title="Cumulative (THB)" fmt='#,##0' />
    <Column id=comment title="Comment" />
</DataTable>
