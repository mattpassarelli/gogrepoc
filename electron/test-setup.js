// Simple test script to verify Electron setup
// This script checks that all required modules can be loaded

const path = require('path');
const fs = require('fs');

console.log('Testing Electron project setup...\n');

// Test 1: Check that required files exist
const requiredFiles = [
  'package.json',
  'main.js',
  'preload.js',
  'renderer/index.html',
  'README.md'
];

let allFilesExist = true;
console.log('1. Checking required files:');
requiredFiles.forEach(file => {
  const exists = fs.existsSync(path.join(__dirname, file));
  console.log(`   ${exists ? '✓' : '✗'} ${file}`);
  if (!exists) allFilesExist = false;
});

if (!allFilesExist) {
  console.error('\n❌ Some required files are missing!');
  process.exit(1);
}

// Test 2: Check that dependencies are installed
console.log('\n2. Checking dependencies:');
const requiredDeps = [
  'electron',
  'electron-builder',
  'electron-store',
  'electron-log',
  'concurrently'
];

let allDepsInstalled = true;
requiredDeps.forEach(dep => {
  try {
    require.resolve(dep);
    console.log(`   ✓ ${dep}`);
  } catch (e) {
    console.log(`   ✗ ${dep}`);
    allDepsInstalled = false;
  }
});

if (!allDepsInstalled) {
  console.error('\n❌ Some dependencies are not installed!');
  console.error('Run: npm install');
  process.exit(1);
}

// Test 3: Verify package.json configuration
console.log('\n3. Checking package.json configuration:');
const pkg = require('./package.json');

const checks = [
  { name: 'main entry point', value: pkg.main === 'main.js' },
  { name: 'electron-builder config', value: !!pkg.build },
  { name: 'Windows target', value: !!pkg.build?.win },
  { name: 'macOS target', value: !!pkg.build?.mac },
  { name: 'Linux target', value: !!pkg.build?.linux },
  { name: 'dev script', value: !!pkg.scripts?.dev },
  { name: 'build script', value: !!pkg.scripts?.build }
];

let allChecksPass = true;
checks.forEach(check => {
  console.log(`   ${check.value ? '✓' : '✗'} ${check.name}`);
  if (!check.value) allChecksPass = false;
});

if (!allChecksPass) {
  console.error('\n❌ Some configuration checks failed!');
  process.exit(1);
}

// Test 4: Verify build directory exists
console.log('\n4. Checking build directory:');
const buildDirExists = fs.existsSync(path.join(__dirname, 'build'));
console.log(`   ${buildDirExists ? '✓' : '✗'} build/ directory exists`);

if (!buildDirExists) {
  console.error('\n❌ Build directory is missing!');
  process.exit(1);
}

console.log('\n✅ All setup checks passed!');
console.log('\nNext steps:');
console.log('  - Add application icons to build/ directory');
console.log('  - Run "npm run dev:electron" to test the app');
console.log('  - Continue with Task 2: Python backend bundling');
