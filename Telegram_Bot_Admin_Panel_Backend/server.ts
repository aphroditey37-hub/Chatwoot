import express, { Request, Response, NextFunction } from "express";
import cors from "cors";
import dotenv from "dotenv";
import { getDatabase } from "./database/index.js";
import { reviewer as reviewers } from "./database/schema.js";
import { desc, eq } from "drizzle-orm";
import path from "path";
import { fileURLToPath } from "url";

dotenv.config();

const app = express();
app.set("trust proxy", true);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = Number(process.env.PORT || 5055);
const ADMIN_SECRET = process.env.ADMIN_SECRET || "";
const CORS_ORIGIN =
    process.env.CORS_ORIGIN || "https://chatwoot-telelgram.joycegames.vip";

const db = await getDatabase();

if (!ADMIN_SECRET) {
    console.log("⚠️ ADMIN_SECRET missing. Set it in .env (required).");
    process.exit(1);
}

app.use(express.json({ limit: "200kb" }));

app.use(
    cors({
        origin: CORS_ORIGIN,
        credentials: false,
    }),
);

function requireAdmin(req: Request, res: Response, next: NextFunction) {
    const secret = req.header("x-admin-secret");
    if (!secret || secret !== ADMIN_SECRET) {
        return res.status(401).json({ ok: false, message: "Unauthorized" });
    }
    next();
}

app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, "index.html"));
});

app.get("/health", (_req: Request, res: Response) => {
    res.json({ ok: true, service: "tg-admin-api", ts: Date.now() });
});

app.use(requireAdmin);

function normalizeTelegramId(input: unknown): string | null {
    if (input === undefined || input === null) return null;
    const s = String(input).trim();
    if (!/^\d+$/.test(s)) return null;
    return s;
}

function normalizeUsername(input: unknown): string | null {
    if (!input) return null;
    let s = String(input).trim();
    if (!s) return null;
    if (s.startsWith("@")) s = s.slice(1);
    if (!/^[A-Za-z0-9_]{3,32}$/.test(s)) return null;
    return s;
}

app.get("/list", async (_req: Request, res: Response) => {
    const data = await db
        .select()
        .from(reviewers)
        .orderBy(desc(reviewers.createdAt));

    res.json({ ok: true, reviewers: data });
});

app.post("/add", async (req: Request, res: Response) => {
    const username = normalizeUsername(req.body?.username);

    if (!username) {
        return res.status(400).json({
            ok: false,
            message: "Provide username (@username)",
        });
    }
    if (username) {
        const existing = await db
            .select()
            .from(reviewers)
            .where(eq(reviewers.username, username))
            .limit(1);

        if (existing.length > 0) {
            return res.json({
                ok: true,
                message: "Already exists",
                reviewer: existing[0],
            });
        }

        const [inserted] = await db
            .insert(reviewers)
            .values({
                username,
            })
            .returning();

        return res.json({
            ok: true,
            message: "Added",
            reviewer: inserted,
        });
    }
});

app.post("/remove", async (req: Request, res: Response) => {
    const username = normalizeUsername(req.body?.username);

    if (!username) {
        return res.status(400).json({
            ok: false,
            message: "Provide username",
        });
    }

    const result = await db
        .delete(reviewers)
        .where(eq(reviewers.username, username))
        .returning({ id: reviewers.id });

    res.json({
        ok: true,
        deleted: result.length,
    });
});

app.listen(PORT, () => {
    console.log(`🚀 TG Admin API running on :${PORT}`);
    console.log(`✅ CORS_ORIGIN: ${CORS_ORIGIN}`);
});
