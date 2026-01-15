// src/controllers/tag.controller.js
const Tag = require("../models/tag.model");

// Create a text tag
// Expected body: { title, type, text }
exports.createTag = async (req, res) => {
  try {
    const { title, type, text } = req.body || {};
    if (!title || !type || !text) {
      return res.status(400).json("title, type and text are required");
    }

    const doc = await Tag.create({
      title: String(title).trim(),
      type: String(type).trim().toLowerCase(),
      text: String(text).trim(),
    });

    return res.status(201).json({
      _id: doc._id,
      title: doc.title,
      type: doc.type,
      text: doc.text,
      uploadedAt: doc.uploadedAt,
    });
  } catch (err) {
    console.error("[createTag] error:", err);
    return res.status(500).json("Failed to create tag");
  }
};

// Get all tags (newest first)
exports.getTags = async (_req, res) => {
  try {
    const tags = await Tag.find({}).sort({ uploadedAt: -1 }).lean();
    // Normalize fields the frontend uses
    const out = tags.map((t) => ({
      _id: t._id,
      title: t.title,
      type: t.type,
      text: t.text,
      uploadedAt: t.uploadedAt,
    }));
    return res.json(out);
  } catch (err) {
    console.error("[getTags] error:", err);
    return res.status(500).json("Failed to fetch tags");
  }
};

// Get latest tag (optionally by type)
// /api/tags/latest?type=cashapp
exports.getLatestTag = async (req, res) => {
  try {
    const { type } = req.query || {};
    const query = {};

    if (type) {
      query.type = String(type).toLowerCase().trim();
    }

    const doc = await Tag.findOne(query).sort({ uploadedAt: -1 }).lean();
    if (!doc) return res.status(404).json("No tag found");

    return res.json({
      _id: doc._id,
      title: doc.title,
      type: doc.type,
      text: doc.text,
      uploadedAt: doc.uploadedAt,
    });
  } catch (err) {
    console.error("[getLatestTag] error:", err);
    return res.status(500).json("Failed to fetch latest tag");
  }
};

// Delete a tag by id
exports.deleteTag = async (req, res) => {
  try {
    const { id } = req.params;
    const doc = await Tag.findById(id);
    if (!doc) return res.status(404).json("Tag not found");

    // No Cloudinary cleanup necessary anymore.
    await Tag.findByIdAndDelete(id);
    return res.json({ ok: true });
  } catch (err) {
    console.error("[deleteTag] error:", err);
    return res.status(500).json("Failed to delete tag");
  }
};
