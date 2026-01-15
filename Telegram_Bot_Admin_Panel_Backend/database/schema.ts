import { pgTable, text, timestamp, serial } from "drizzle-orm/pg-core";

export const reviewer = pgTable("reviewer", {
    id: serial("id").primaryKey(),
    username: text("username"),
    chatId: text("chat_id"),
    createdAt: timestamp("created_at").defaultNow(),
});
