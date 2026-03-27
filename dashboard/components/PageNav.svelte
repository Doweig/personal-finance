<script>
    export let active = "home"; // home | restaurants | returns
    export let context = "";
</script>

<nav class="pf-nav">
    <a href="/" class:active={active === "home"}>Home</a>
    <a href="/restaurants" class:active={active === "restaurants"}>Restaurants</a>
    <a href="/returns" class:active={active === "returns"}>Returns</a>
    {#if context}
        <span class="context">{context}</span>
    {/if}
</nav>

<style>
    .pf-nav {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.6rem;
        border-radius: 14px;
        background: linear-gradient(120deg, #f5f9ff 0%, #fff7ec 100%);
        border: 1px solid #dce9fb;
        flex-wrap: wrap;
        margin-bottom: 1rem;
        font-family: "Avenir Next", "Segoe UI", sans-serif;
    }

    .pf-nav a {
        text-decoration: none;
        color: #21415e;
        background: #ffffff;
        border: 1px solid #c9d9ee;
        border-radius: 999px;
        padding: 0.35rem 0.8rem;
        font-size: 0.86rem;
        font-weight: 600;
    }

    .pf-nav a.active {
        background: #20466a;
        border-color: #20466a;
        color: #fffaf2;
    }

    .pf-nav .context {
        margin-left: auto;
        color: #4a647a;
        font-size: 0.8rem;
        font-weight: 600;
    }

    @media (max-width: 640px) {
        .pf-nav .context {
            width: 100%;
            margin-left: 0;
            margin-top: 0.25rem;
        }
    }
</style>
