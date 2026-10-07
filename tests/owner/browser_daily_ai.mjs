// Deliberately isolated transport fixture; no credentials or real provider calls.
process.env.OWNER_DIAGNOSIS_AI_FIXTURE='1';
await import('./browser_diagnosis.mjs');
