process.env.OWNER_MARKET_FULL='1';
delete process.env.OWNER_MARKET_FLAT;
await import('./browser_market_history.mjs');
