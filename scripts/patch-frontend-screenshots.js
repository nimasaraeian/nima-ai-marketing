/**
 * Node.js script to patch frontend screenshot extraction
 * Run with: node scripts/patch-frontend-screenshots.js
 */

const fs = require('fs');
const path = require('path');

console.log('🔧 Patching frontend screenshot extraction...\n');

// Try to find the file
const possiblePaths = [
  '../www.nimasaraeian.com/app/ai-marketing/decision-brain/page.tsx',
  '../../www.nimasaraeian.com/app/ai-marketing/decision-brain/page.tsx',
  path.join(process.env.HOME || process.env.USERPROFILE, 'Documents/GitHub/www.nimasaraeian.com/app/ai-marketing/decision-brain/page.tsx'),
  'app/ai-marketing/decision-brain/page.tsx'
];

let filePath = null;
for (const possiblePath of possiblePaths) {
  const fullPath = path.resolve(possiblePath);
  if (fs.existsSync(fullPath)) {
    filePath = fullPath;
    console.log(`✅ Found file at: ${filePath}`);
    break;
  }
}

if (!filePath) {
  console.log('❌ Could not find page.tsx file automatically.');
  console.log('Please update the file manually using FRONTEND_PATCH.md');
  process.exit(1);
}

console.log('📝 Reading file...');
let content = fs.readFileSync(filePath, 'utf8');

// Check if already patched
if (content.includes('data?.screenshots?.desktop?.url')) {
  console.log('✅ File already patched!');
  process.exit(0);
}

// Find and replace the problematic code
const oldPattern = /(const\s+desktopSrc\s*=.*?)(const\s+mobileSrc\s*=.*?)(console\.log\("📥 Desktop source:".*?desktopSrc\.substring)/s;

if (oldPattern.test(content)) {
  console.log('🔍 Found code to patch...');
  
  const replacement = `// Extract screenshot URLs (supports new schema: object with .url property)
const getScreenshotUrl = (screenshot: any): string => {
  if (!screenshot) return "";
  if (typeof screenshot === "object" && screenshot?.url) {
    return screenshot.url;
  }
  if (typeof screenshot === "string") {
    return screenshot;
  }
  return "";
};

const desktopSrc = getScreenshotUrl(data?.screenshots?.desktop);
const mobileSrc = getScreenshotUrl(data?.screenshots?.mobile);

console.log("📥 Desktop source:", desktopSrc ? \`\${desktopSrc.substring(0, 50)}...\` : "NOT FOUND");`;
  
  // Create backup
  const backupPath = `${filePath}.backup`;
  fs.copyFileSync(filePath, backupPath);
  console.log(`💾 Backup created: ${backupPath}`);
  
  // Replace
  content = content.replace(oldPattern, replacement);
  
  // Write new content
  fs.writeFileSync(filePath, content, 'utf8');
  
  console.log('✅ File patched successfully!');
  console.log('📋 Changes:');
  console.log('  - Added getScreenshotUrl helper function');
  console.log('  - Updated desktopSrc extraction to use new schema');
  console.log('  - Updated mobileSrc extraction to use new schema');
} else {
  console.log('⚠️ Could not find exact pattern to patch.');
  console.log('Please manually update the file using FRONTEND_PATCH.md');
  process.exit(1);
}

console.log('\n✅ Done! The frontend should now work with the new screenshot schema.');


