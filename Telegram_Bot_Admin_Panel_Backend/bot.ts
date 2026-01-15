// bot.js (ESM)
import "dotenv/config";
import { Telegraf } from "telegraf";

const token = process.env.TELEGRAM_BOT_TOKEN;
if (!token) throw new Error("Missing TELEGRAM_BOT_TOKEN");

const bot = new Telegraf(token);

// Optional: keep commands (won’t run unless polling/webhook calls it)
bot.start((ctx) => ctx.reply("✅ Reviewer bot alive (webhook handled elsewhere)."));
bot.command("ping", (ctx) => ctx.reply("pong ✅"));

// IMPORTANT: disable polling so it doesn't steal callback_query updates
const ENABLE_POLLING = process.env.ENABLE_TG_POLLING === "true";

if (ENABLE_POLLING) {
  bot.launch().then(() => console.log("🚀 Telegram bot polling enabled"));
} else {
  console.log("✅ Polling disabled (middleware webhook will receive button clicks).");
}

// Graceful stop (optional)
process.once("SIGINT", () => bot.stop("SIGINT"));
process.once("SIGTERM", () => bot.stop("SIGTERM"));
