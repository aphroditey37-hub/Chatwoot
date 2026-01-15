import "dotenv/config";
import { drizzle, NodePgDatabase } from "drizzle-orm/node-postgres";
import * as schema from "./schema.ts";

let db: NodePgDatabase<typeof schema> | null = null;

export async function getDatabase(): Promise<NodePgDatabase<typeof schema>> {
    if (!db) {
        db = db = drizzle(process.env.DATABASE_URL!, { schema });
    }

    return db;
}
