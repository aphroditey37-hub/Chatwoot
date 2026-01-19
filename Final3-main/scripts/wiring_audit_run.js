#!/usr/bin/env node
/**
 * Wiring Audit Runner
 * 
 * Compares frontend-declared API paths with backend mounted routes.
 * Identifies broken calls (frontend paths not in backend) and unused routes.
 * 
 * Usage: node scripts/wiring_audit_run.js [--backend-url URL]
 * 
 * Exit codes:
 *   0 = All frontend paths have matching backend routes
 *   1 = Broken calls detected (frontend paths missing from backend)
 */

const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

// Configuration
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8001';
const DEV_ENDPOINT = '/api/v1/dev/wiring/routes';

/**
 * Fetch backend routes from dev endpoint
 */
async function fetchBackendRoutes() {
  return new Promise((resolve, reject) => {
    const url = `${BACKEND_URL}${DEV_ENDPOINT}`;
    const client = url.startsWith('https') ? https : http;
    
    console.log(`Fetching backend routes from: ${url}`);
    
    client.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          if (res.statusCode === 404) {
            reject(new Error('Dev wiring endpoint not available (production mode or not mounted)'));
            return;
          }
          if (res.statusCode !== 200) {
            reject(new Error(`HTTP ${res.statusCode}: ${data}`));
            return;
          }
          const json = JSON.parse(data);
          resolve(json.routes || []);
        } catch (e) {
          reject(new Error(`Failed to parse response: ${e.message}`));
        }
      });
    }).on('error', reject);
  });
}

/**
 * Load frontend paths from extraction output
 */
function loadFrontendPaths() {
  // Check multiple possible locations
  const possiblePaths = [
    path.join(__dirname, 'frontend_paths.json'),
    path.join(__dirname, '..', 'frontend', 'scripts', 'frontend_paths.json'),
    path.join(__dirname, '..', 'scripts', 'frontend_paths.json'),
  ];
  
  let filePath = possiblePaths.find(p => fs.existsSync(p));
  
  if (!filePath) {
    console.log('Frontend paths not found. Running extraction...\n');
    
    // Run extraction script
    const { execSync } = require('child_process');
    const frontendScriptPath = path.join(__dirname, '..', 'frontend', 'scripts', 'wiring_audit_extract_paths.js');
    
    try {
      execSync(`node "${frontendScriptPath}"`, {
        cwd: path.join(__dirname, '..'),
        stdio: 'inherit'
      });
    } catch (e) {
      throw new Error('Failed to extract frontend paths');
    }
    
    // Re-check for the file
    filePath = possiblePaths.find(p => fs.existsSync(p));
  }
  
  if (!filePath) {
    throw new Error('Frontend paths file not created. Check extraction script output.');
  }
  
  console.log(`Loading frontend paths from: ${filePath}`);
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

/**
 * Normalize path for comparison (handle {param} vs {user_id} etc)
 */
function normalizeForComparison(pathStr) {
  return pathStr
    // Normalize all path parameters to {param}
    .replace(/\{[^}]+\}/g, '{param}')
    // Remove trailing slashes
    .replace(/\/+$/, '')
    // Lowercase for comparison
    .toLowerCase();
}

/**
 * Check if a frontend path has a matching backend route
 */
function hasMatchingRoute(frontendPath, backendRoutes) {
  const normalizedFrontend = normalizeForComparison(frontendPath.path);
  const frontendMethod = frontendPath.method.toUpperCase();
  
  for (const backend of backendRoutes) {
    const normalizedBackend = normalizeForComparison(backend.path);
    const backendMethod = backend.method.toUpperCase();
    
    // Method-aware matching
    if (normalizedFrontend === normalizedBackend && frontendMethod === backendMethod) {
      return true;
    }
    
    // Path-only matching (for cases where method might differ)
    if (normalizedFrontend === normalizedBackend) {
      return { partial: true, expectedMethod: backendMethod };
    }
  }
  
  return false;
}

/**
 * Find unused backend routes
 */
function findUnusedRoutes(backendRoutes, frontendPaths) {
  const unused = [];
  
  for (const backend of backendRoutes) {
    const normalizedBackend = normalizeForComparison(backend.path);
    
    // Skip dev/wiring routes
    if (backend.path.includes('/dev/wiring')) continue;
    
    const isUsed = frontendPaths.some(frontend => {
      const normalizedFrontend = normalizeForComparison(frontend.path);
      return normalizedFrontend === normalizedBackend;
    });
    
    if (!isUsed) {
      unused.push(backend);
    }
  }
  
  return unused;
}

/**
 * Main audit function
 */
async function runAudit() {
  console.log('╔══════════════════════════════════════════════════════════════╗');
  console.log('║              WIRING AUDIT REPORT                             ║');
  console.log('╚══════════════════════════════════════════════════════════════╝\n');
  
  try {
    // 1. Fetch backend routes
    const backendRoutes = await fetchBackendRoutes();
    console.log(`✓ Backend routes loaded: ${backendRoutes.length}\n`);
    
    // 2. Load frontend paths
    const frontendPaths = loadFrontendPaths();
    console.log(`✓ Frontend paths loaded: ${frontendPaths.length}\n`);
    
    // 3. Find broken calls (frontend paths not in backend)
    const brokenCalls = [];
    const methodMismatches = [];
    
    for (const frontend of frontendPaths) {
      const match = hasMatchingRoute(frontend, backendRoutes);
      
      if (!match) {
        brokenCalls.push(frontend);
      } else if (match.partial) {
        methodMismatches.push({
          ...frontend,
          expectedMethod: match.expectedMethod
        });
      }
    }
    
    // 4. Find unused backend routes
    const unusedRoutes = findUnusedRoutes(backendRoutes, frontendPaths);
    
    // 5. Print report
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('                         SUMMARY');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log(`  Backend Routes:     ${backendRoutes.length}`);
    console.log(`  Frontend Paths:     ${frontendPaths.length}`);
    console.log(`  ─────────────────────────────────────────────────────────────`);
    console.log(`  BROKEN CALLS:       ${brokenCalls.length} ${brokenCalls.length > 0 ? '❌ FAIL' : '✅ PASS'}`);
    console.log(`  Method Mismatches:  ${methodMismatches.length}`);
    console.log(`  Unused Routes:      ${unusedRoutes.length} (informational)`);
    console.log('═══════════════════════════════════════════════════════════════\n');
    
    // 6. Detail broken calls
    if (brokenCalls.length > 0) {
      console.log('❌ BROKEN CALLS (Frontend paths not in backend):');
      console.log('─────────────────────────────────────────────────────────────');
      for (const broken of brokenCalls.slice(0, 20)) {
        console.log(`  ${broken.method.padEnd(6)} ${broken.path}`);
        console.log(`         Source: ${broken.source}`);
      }
      if (brokenCalls.length > 20) {
        console.log(`  ... and ${brokenCalls.length - 20} more`);
      }
      console.log('');
    }
    
    // 7. Detail method mismatches
    if (methodMismatches.length > 0) {
      console.log('⚠️  METHOD MISMATCHES:');
      console.log('─────────────────────────────────────────────────────────────');
      for (const mm of methodMismatches.slice(0, 10)) {
        console.log(`  ${mm.path}`);
        console.log(`    Frontend: ${mm.method}, Backend expects: ${mm.expectedMethod}`);
      }
      console.log('');
    }
    
    // 8. Sample unused routes
    if (unusedRoutes.length > 0 && process.argv.includes('--show-unused')) {
      console.log('ℹ️  UNUSED BACKEND ROUTES (not referenced by frontend):');
      console.log('─────────────────────────────────────────────────────────────');
      for (const unused of unusedRoutes.slice(0, 15)) {
        console.log(`  ${unused.method.padEnd(6)} ${unused.path}`);
      }
      if (unusedRoutes.length > 15) {
        console.log(`  ... and ${unusedRoutes.length - 15} more`);
      }
      console.log('');
    }
    
    // 9. Exit code
    if (brokenCalls.length > 0) {
      console.log('══════════════════════════════════════════════════════════════');
      console.log('  RESULT: ❌ FAIL - Broken calls detected');
      console.log('══════════════════════════════════════════════════════════════');
      process.exit(1);
    } else {
      console.log('══════════════════════════════════════════════════════════════');
      console.log('  RESULT: ✅ PASS - All frontend paths have backend routes');
      console.log('══════════════════════════════════════════════════════════════');
      process.exit(0);
    }
    
  } catch (error) {
    console.error('❌ Audit failed:', error.message);
    process.exit(2);
  }
}

// Run
runAudit();
