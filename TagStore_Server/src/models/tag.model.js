// src/models/tag.model.js
const mongoose = require("mongoose");

const tagSchema = new mongoose.Schema(
  {
    title: { type: String, required: true, trim: true },
    type: {
      type: String,
      required: true,
      enum: ["cashapp", "chime", "other"],
      lowercase: true,
      trim: true,
    },
    // NEW: plain text tag (e.g., "$hello123")
    text: { type: String, required: true, trim: true },

    // DEPRECATED (from image version): url, public_id
    // Keeping no longer needed fields out of the schema to keep data clean.
  },
  { timestamps: { createdAt: "uploadedAt", updatedAt: "updatedAt" } }
);

module.exports = mongoose.model("Tag", tagSchema);
