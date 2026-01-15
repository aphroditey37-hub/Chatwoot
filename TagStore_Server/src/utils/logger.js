// src/utils/logger.js
module.exports = {
  info: (...args) => console.log("ℹ️", ...args),
  error: (...args) => console.error("❌", ...args),
  debug: (...args) => console.log("🐞", ...args),
};
