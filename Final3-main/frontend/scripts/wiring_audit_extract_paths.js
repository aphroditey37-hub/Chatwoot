#!/usr/bin/env node
/**
 * Wiring Audit - Extract API Paths from Frontend Code
 * 
 * Scans frontend API files and extracts all declared API paths.
 * Normalizes paths for comparison with backend routes.
 * 
 * Usage: node frontend/scripts/wiring_audit_extract_paths.js
 */

const fs = require('fs');
const path = require('path');

// Files to scan for API calls
const API_FILES = [
  'src/api/admin.js',
  'src/api/endpoints.js',
  'src/api/http.js',
  'src/api/index.js',
];

// Regex patterns to extract API paths
const PATTERNS = [
  // http.get('/path'), http.post('/path'), etc.
  /http\.(get|post|put|delete|patch)\s*\(\s*[`'"]([^`'"]+)[`'"]/gi,
  // http.get(`/path/${var}`)
  /http\.(get|post|put|delete|patch)\s*\(\s*`([^`]+)`/gi,
  // Standalone string paths that look like API endpoints
  /[`'"](\/(admin|auth|wallet|payments|portal|orders|games|referrals|rewards|promotions|telegram|webhooks|identity|analytics|bot|credit|withdrawal|public)[^`'"]*)[`'"]/gi,
];

/**
 * Normalize a path for comparison:
 * - Remove query strings
 * - Replace template literals ${...} with {param}
 * - Replace UUID-like segments with {id}
 * - Ensure leading slash
 * - Remove incomplete template expressions
 */
function normalizePath(rawPath) {
  let normalized = rawPath
    // Remove incomplete template expressions like ${queryStr at end
    .replace(/\$\{[^}]*$/, '')
    // Remove query strings (including template ones)
    .replace(/\?.*$/, '')
    .replace(/\$\{query.*$/i, '')
    // Replace ${variable} with {param}
    .replace(/\$\{[^}]+\}/g, '{param}')
    // Replace backtick interpolation leftovers
    .replace(/`/g, '')
    // Remove trailing incomplete paths
    .replace(/\{[^}]*$/, '')
    // Clean up any double slashes
    .replace(/\/+/g, '/')
    // Remove trailing slash
    .replace(/\/$/, '')
    // Ensure starts with /
    .replace(/^([^/])/, '/$1');
  
  return normalized;
}

/**
 * Extract method from the regex match
 */
function extractMethod(match) {
  const methodMatch = match.match(/http\.(get|post|put|delete|patch)/i);
  return methodMatch ? methodMatch[1].toUpperCase() : 'GET';
}

/**
 * Scan a file for API paths
 */
function scanFile(filePath, baseDir) {
  const fullPath = path.join(baseDir, filePath);
  
  if (!fs.existsSync(fullPath)) {
    console.warn(`  [SKIP] ${filePath} - not found`);
    return [];
  }
  
  const content = fs.readFileSync(fullPath, 'utf8');
  const paths = [];
  const seen = new Set();
  
  for (const pattern of PATTERNS) {
    // Reset regex state
    pattern.lastIndex = 0;
    
    let match;
    while ((match = pattern.exec(content)) !== null) {
      const method = extractMethod(match[0]);
      const rawPath = match[2] || match[1];
      
      // Skip if not an API path
      if (!rawPath || !rawPath.startsWith('/')) continue;
      
      // Skip if it's a React route (contains 'client/' without 'api')
      if (rawPath.includes('/client/') && !rawPath.includes('/api/')) continue;
      
      // Skip docs/openapi paths
      if (rawPath.includes('/docs') || rawPath.includes('/openapi')) continue;
      
      const normalized = normalizePath(rawPath);
      const key = `${method}:${normalized}`;
      
      if (!seen.has(key)) {
        seen.add(key);
        paths.push({
          method,
          path: normalized,
          raw: rawPath,
          source: filePath
        });
      }
    }
  }
  
  return paths;
}

/**
 * Main extraction function
 */
function extractPaths() {
  console.log('=== Frontend API Path Extraction ===\n');
  
  // Determine base directory (frontend root)
  const scriptDir = __dirname;
  const baseDir = path.resolve(scriptDir, '..');
  
  console.log(`Base directory: ${baseDir}\n`);
  
  const allPaths = [];
  
  for (const file of API_FILES) {
    console.log(`Scanning: ${file}`);
    const paths = scanFile(file, baseDir);
    console.log(`  Found: ${paths.length} paths`);
    allPaths.push(...paths);
  }
  
  // Deduplicate by method+path
  const uniquePaths = [];
  const seen = new Set();
  
  for (const p of allPaths) {
    // Ensure path has /api/v1 prefix for comparison
    let fullPath = p.path;
    if (!fullPath.startsWith('/api/v1')) {
      fullPath = '/api/v1' + fullPath;
    }
    
    const key = `${p.method}:${fullPath}`;
    if (!seen.has(key)) {
      seen.add(key);
      uniquePaths.push({
        method: p.method,
        path: fullPath,
        source: p.source
      });
    }
  }
  
  console.log(`\nTotal unique paths: ${uniquePaths.length}`);
  
  return uniquePaths;
}

// Run if called directly
if (require.main === module) {
  const paths = extractPaths();
  
  // Output as JSON for piping to comparator
  const outputFile = path.join(process.cwd(), 'scripts', 'frontend_paths.json');
  fs.writeFileSync(outputFile, JSON.stringify(paths, null, 2));
  console.log(`\nSaved to: ${outputFile}`);
}

module.exports = { extractPaths, normalizePath };
