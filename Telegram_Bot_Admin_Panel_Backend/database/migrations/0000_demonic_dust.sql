CREATE TABLE "reviewer" (
	"id" serial PRIMARY KEY NOT NULL,
	"username" text,
	"chat_id" text,
	"created_at" timestamp DEFAULT now()
);
