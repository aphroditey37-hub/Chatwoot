// src/app.js (excerpt)
const express = require("express");
const app = express();
const cors = require("cors");
const morgan = require("morgan");

app.use(cors());
app.use(express.json()); // <- REQUIRED for JSON body
app.use(morgan("dev"));

// routes
const tagRoutes = require("./routes/tag.routes");
app.use("/api/tags", tagRoutes);

// 404 + error handlers remain the same
module.exports = app;
