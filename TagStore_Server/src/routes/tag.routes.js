// src/routes/tag.routes.js
const express = require("express");
const router = express.Router();
const {
  createTag,
  getTags,
  getLatestTag,
  deleteTag,
} = require("../controllers/tag.controller");

// NOTE: Old image routes used multer; not needed now. We accept JSON.
// Ensure app.js includes: app.use(express.json());

router.post("/", createTag); // JSON { title, type, text }
router.get("/", getTags); // list all
router.get("/latest", getLatestTag); // latest overall or by ?type=
router.delete("/:id", deleteTag); // remove by id

module.exports = router;
