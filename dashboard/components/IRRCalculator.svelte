<script>
    export let cashflows = [];  // array of {months_ago: number, amount: number}

    function solveIRR(cfs, guess = 0.01, maxIter = 200, tol = 1e-8) {
        let r = guess;
        for (let i = 0; i < maxIter; i++) {
            let npv = 0;
            let dnpv = 0;
            for (const cf of cfs) {
                const t = cf.months_ago;
                const pv = cf.amount / Math.pow(1 + r, t);
                npv += pv;
                dnpv -= t * cf.amount / Math.pow(1 + r, t + 1);
            }
            if (Math.abs(npv) < tol) break;
            if (Math.abs(dnpv) < tol) break;
            r = r - npv / dnpv;
            if (r < -0.99) r = -0.5;
            if (r > 10) r = 1;
        }
        return r;
    }

    $: monthlyIRR = cashflows.length > 0 ? solveIRR(cashflows) : null;
    $: annualIRR = monthlyIRR !== null ? Math.pow(1 + monthlyIRR, 12) - 1 : null;
</script>

{#if monthlyIRR !== null}
    <div style="display: flex; gap: 1rem;">
        <div>
            <div style="font-size: 0.75rem; color: var(--grey-600); text-transform: uppercase;">Monthly IRR</div>
            <div style="font-size: 1.5rem; font-weight: 700;">{(monthlyIRR * 100).toFixed(2)}%</div>
        </div>
        <div>
            <div style="font-size: 0.75rem; color: var(--grey-600); text-transform: uppercase;">Annualized</div>
            <div style="font-size: 1.5rem; font-weight: 700;">{(annualIRR * 100).toFixed(1)}%</div>
        </div>
    </div>
{:else}
    <div style="color: var(--grey-500);">Insufficient data for IRR calculation</div>
{/if}
