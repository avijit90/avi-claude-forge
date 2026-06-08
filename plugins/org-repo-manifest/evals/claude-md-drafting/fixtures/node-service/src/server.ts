import express from "express";
const app = express();
app.post("/notify", (_req, res) => res.json({ ok: true }));
app.listen(3000);
