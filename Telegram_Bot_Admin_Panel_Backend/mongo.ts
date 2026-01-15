import { MongoClient, Db } from "mongodb";
import "dotenv/config";

const uri = process.env.MONGO_URI;
if (!uri) {
    throw new Error("❌ MONGO_URI missing in .env");
}

let client: MongoClient | null = null;
let db: Db | null = null;

export async function connectToMongo(): Promise<Db> {
    if (db) return db;

    client = new MongoClient(uri, {
        maxPoolSize: 10,
    });

    await client.connect();
    db = client.db(); // default DB from URI

    console.log("✅ Connected to MongoDB");
    return db;
}
