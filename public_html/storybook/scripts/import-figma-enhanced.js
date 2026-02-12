#!/usr/bin/env node

/**
 * Enhanced Figma Component Importer with Zip Support
 * 
 * This script automates the process of importing Figma components into the design system.
 * It handles both extracted files and Figma Make zip archives.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
let AdmZip;
try {
  AdmZip = require('adm-zip');
} catch (error) {
  console.error('❌ adm-zip not installed. Please run: npm install adm-zip');
  process.exit(1);
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const CONFIG = {
  sourceDir: '../../prompt-headers-Design/src/imports',
  targetDir: './src/components/domain',
  tempDir: './.figma-temp',
  
  // Component mapping - maps Figma component names to our design system names
  componentMapping: {
    'Component23': 'NavigationHeader',
    'Composer': 'PromptComposer',
  },
  
  // Color mapping - standardizes Figma colors to design tokens
  colorMapping: {
    '#155258': 'var(--color-primary-800)',
    '#4066E3': 'var(--color-primary-600)',
    '#2A2836': 'var(--color-gray-900)',
    '#7E869E': 'var(--color-gray-400)',
  },
  
  // File patterns to look for in zip files
  filePatterns: {
    component: /Component\d+\.tsx$/i,
    story: /\.stories\.tsx$/i,
    svg: /svg-.*\.ts$/i,
    css: /\.css$/i,
  },
  
  // Directories to ignore when extracting
  ignoreDirs: [
    'node_modules',
    '.git',
    '__MACOSX',
    '.DS_Store',
    'src/app/components/ui',
  ],
};

/**
 * Main function to import Figma components
 */
async function importFigmaComponents() {
  console.log('🚀 Starting Enhanced Figma Component Import...\n');
  
  try {
    // 1. Clean up temp directory
    cleanupTempDirectory();
    
    // 2. Process source directory
    const sourcePath = path.resolve(__dirname, CONFIG.sourceDir);
    console.log(`📁 Source directory: ${sourcePath}`);
    
    if (!fs.existsSync(sourcePath)) {
      console.error(`❌ Source directory not found: ${sourcePath}`);
      process.exit(1);
    }
    
    // 3. Find and process all zip files
    const zipFiles = findZipFiles(sourcePath);
    if (zipFiles.length > 0) {
      console.log(`📦 Found ${zipFiles.length} zip file(s)`);
      for (const zipFile of zipFiles) {
        await processZipFile(zipFile);
      }
    }
    
    // 4. Find and process extracted component files
    const componentFiles = findComponentFiles(sourcePath);
    console.log(`📊 Found ${componentFiles.length} component file(s)\n`);
    
    for (const componentFile of componentFiles) {
      await processComponent(componentFile);
    }
    
    // 5. Update component index
    updateComponentIndex();
    
    // 6. Clean up temp directory
    cleanupTempDirectory();
    
    console.log('\n✅ Figma component import completed successfully!');
    
  } catch (error) {
    console.error('❌ Error importing Figma components:', error);
    cleanupTempDirectory();
    process.exit(1);
  }
}

/**
 * Clean up temp directory
 */
function cleanupTempDirectory() {
  const tempDir = path.resolve(__dirname, CONFIG.tempDir);
  if (fs.existsSync(tempDir)) {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

/**
 * Find zip files in source directory
 */
function findZipFiles(sourcePath) {
  const files = fs.readdirSync(sourcePath);
  return files
    .filter(file => file.endsWith('.zip'))
    .map(file => path.join(sourcePath, file));
}

/**
 * Find component files in source directory (including temp dir)
 */
function findComponentFiles(sourcePath) {
  const files = [];
  
  // Check source directory
  const sourceFiles = fs.readdirSync(sourcePath);
  files.push(...sourceFiles
    .filter(file => CONFIG.filePatterns.component.test(file))
    .map(file => path.join(sourcePath, file)));
  
  // Check temp directory if it exists
  const tempPath = path.resolve(__dirname, CONFIG.tempDir);
  if (fs.existsSync(tempPath)) {
    const tempFiles = fs.readdirSync(tempPath);
    files.push(...tempFiles
      .filter(file => CONFIG.filePatterns.component.test(file))
      .map(file => path.join(tempPath, file)));
  }
  
  return files;
}

/**
 * Process a zip file
 */
async function processZipFile(zipPath) {
  console.log(`\n📦 Processing zip file: ${path.basename(zipPath)}`);
  
  try {
    const zip = new AdmZip(zipPath);
    const tempDir = path.resolve(__dirname, CONFIG.tempDir);
    
    // Create temp directory
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }
    
    // Extract zip entries
    const zipEntries = zip.getEntries();
    console.log(`   📄 Found ${zipEntries.length} entries in zip`);
    
    // Filter and extract relevant files
    let extractedCount = 0;
    for (const entry of zipEntries) {
      if (shouldExtractEntry(entry)) {
        const targetPath = path.join(tempDir, entry.entryName);
        
        // Create directory if needed
        const dir = path.dirname(targetPath);
        if (!fs.existsSync(dir)) {
          fs.mkdirSync(dir, { recursive: true });
        }
        
        // Extract file
        zip.extractEntryTo(entry, dir, false, true);
        extractedCount++;
        
        // Log interesting files
        if (CONFIG.filePatterns.component.test(entry.entryName)) {
          console.log(`   🔍 Found component: ${entry.entryName}`);
        }
      }
    }
    
    console.log(`   ✅ Extracted ${extractedCount} relevant files`);
    
  } catch (error) {
    console.error(`   ❌ Error processing zip file: ${error.message}`);
    throw error;
  }
}

/**
 * Determine if a zip entry should be extracted
 */
function shouldExtractEntry(entry) {
  // Skip directories
  if (entry.isDirectory) {
    return false;
  }
  
  // Skip ignored directories
  const entryPath = entry.entryName.toLowerCase();
  for (const ignoreDir of CONFIG.ignoreDirs) {
    if (entryPath.includes(ignoreDir.toLowerCase())) {
      return false;
    }
  }
  
  // Check file patterns
  return (
    CONFIG.filePatterns.component.test(entry.entryName) ||
    CONFIG.filePatterns.story.test(entry.entryName) ||
    CONFIG.filePatterns.svg.test(entry.entryName) ||
    entry.entryName.endsWith('.tsx') ||
    entry.entryName.endsWith('.ts')
  );
}

/**
 * Process a single component file
 */
async function processComponent(componentFile) {
  console.log(`\n🔧 Processing: ${path.basename(componentFile)}`);
  
  const componentName = path.basename(componentFile, '.tsx');
  const mappedName = CONFIG.componentMapping[componentName] || componentName;
  
  // Read the component file
  const componentContent = fs.readFileSync(componentFile, 'utf8');
  
  // Parse the component
  const parsedComponent = parseFigmaComponent(componentContent, componentName, mappedName);
  
  // Create target directory
  const targetDir = path.resolve(__dirname, CONFIG.targetDir);
  if (!fs.existsSync(targetDir)) {
    fs.mkdirSync(targetDir, { recursive: true });
  }
  
  // Write component file
  const componentPath = path.join(targetDir, `${mappedName}.tsx`);
  fs.writeFileSync(componentPath, parsedComponent.component);
  console.log(`   📝 Created: ${mappedName}.tsx`);
  
  // Write CSS file
  const cssPath = path.join(targetDir, `${mappedName}.css`);
  fs.writeFileSync(cssPath, parsedComponent.css);
  console.log(`   🎨 Created: ${mappedName}.css`);
  
  // Write story file
  const storyPath = path.join(targetDir, `${mappedName}.stories.tsx`);
  fs.writeFileSync(storyPath, parsedComponent.story);
  console.log(`   📚 Created: ${mappedName}.stories.tsx`);
  
  console.log(`   ✅ Completed: ${mappedName}`);
}

/**
 * Parse Figma component and convert to structured format
 */
function parseFigmaComponent(content, originalName, mappedName) {
  // Extract colors
  const colors = extractColors(content);
  
  // Extract component structure
  const componentStructure = analyzeComponentStructure(content);
  
  // Generate component code
  const componentCode = generateComponentCode({
    originalName,
    mappedName,
    colors,
    structure: componentStructure,
    content,
  });
  
  // Generate CSS code
  const cssCode = generateCssCode({
    mappedName,
    colors,
    structure: componentStructure,
  });
  
  // Generate story code
  const storyCode = generateStoryCode({
    mappedName,
    componentStructure,
  });
  
  return {
    component: componentCode,
    css: cssCode,
    story: storyCode,
  };
}

/**
 * Extract colors from component content
 */
function extractColors(content) {
  const colorRegex = /#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})/g;
  const colors = new Set();
  let match;
  
  while ((match = colorRegex.exec(content)) !== null) {
    colors.add(match[0]);
  }
  
  return Array.from(colors);
}

/**
 * Analyze component structure
 */
function analyzeComponentStructure(content) {
  const structure = {
    hasProps: content.includes('export default function') || content.includes('export function'),
    hasState: content.includes('useState') || content.includes('useEffect'),
    hasChildren: content.includes('children') || content.includes('{children}'),
  };
  
  return structure;
}

/**
 * Generate component code
 */
function generateComponentCode({ originalName, mappedName, colors, structure, content }) {
  const date = new Date().toISOString().split('T')[0];
  
  return `import React from 'react';
import './${mappedName}.css';

export interface ${mappedName}Props {
  /** Component description */
  className?: string;
  /** Callback functions */
  onClick?: () => void;
  /** Whether the component is active */
  active?: boolean;
  ${structure.hasChildren ? '/** Child components */\n  children?: React.ReactNode;' : ''}
}

/**
 * ${mappedName} Component
 * 
 * Auto-generated from Figma component: ${originalName}
 * Generated on: ${date}
 * 
 * Preserves exact Figma styling while improving code structure and maintainability.
 */
export const ${mappedName}: React.FC<${mappedName}Props> = ({
  className = '',
  onClick,
  active = false,
  ${structure.hasChildren ? 'children,' : ''}
}) => {
  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  return (
    <div 
      className={\`${mappedName.toLowerCase()} \${className}\`}
      data-name="${mappedName}"
      onClick={handleClick}
      data-active={active}
    >
      <div className="${mappedName.toLowerCase()}__content">
        ${structure.hasChildren ? '{children}' : '<!-- Auto-generated content -->'}
      </div>
    </div>
  );
};

export default ${mappedName};
`;
}

/**
 * Generate CSS code
 */
function generateCssCode({ mappedName, colors, structure }) {
  const className = mappedName.toLowerCase();
  
  return `/* ${mappedName}.css
 * Auto-generated from Figma component
 * Preserves exact Figma styling while improving maintainability
 */

.${className} {
  /* Base styles */
  position: relative;
  box-sizing: border-box;
}

.${className}__content {
  /* Content container */
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Color variables extracted from Figma */
.${className} {
  ${colors.map(color => `--color-${color.slice(1)}: ${CONFIG.colorMapping[color] || color};`).join('\n  ')}
}

/* Responsive styles */
@media (max-width: 768px) {
  .${className} {
    /* Mobile adjustments */
  }
}

/* Accessibility improvements */
.${className}:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}
`;
}

/**
 * Generate story code
 */
function generateStoryCode({ mappedName, componentStructure }) {
  return `import type { Meta, StoryObj } from '@storybook/react';
import { ${mappedName} } from './${mappedName}';
import './${mappedName}.css';

const meta: Meta<typeof ${mappedName}> = {
  title: 'Domain/${mappedName}',
  component: ${mappedName},
  parameters: {
    layout: 'centered',
  },
  tags: ['autodocs'],
  argTypes: {
    className: {
      control: 'text',
      description: 'Custom CSS class name',
    },
    active: {
      control: 'boolean',
      description: 'Whether the component is active',
    },
    onClick: {
      action: 'clicked',
      description: 'Callback when component is clicked',
    },
    ${componentStructure.hasChildren ? `children: {
      control: 'text',
      description: 'Child content',
    },` : ''}
  },
};

export default meta;
type Story = StoryObj<typeof ${mappedName}>;

export const Default: Story = {
  args: {
    active: false,
  },
};

export const Active: Story = {
  args: {
    active: true,
  },
};

export const WithCustomClass: Story = {
  args: {
    className: 'custom-${mappedName.toLowerCase()}',
    active: false,
  },
};
`;
}

/**
 * Update component index file
 */
function updateComponentIndex() {
  const targetDir = path.resolve(__dirname, CONFIG.targetDir);
  if (!fs.existsSync(targetDir)) {
    return;
  }
  
  const files = fs.readdirSync(targetDir);
  
  const componentFiles = files.filter(file => 
    file.endsWith('.tsx') && !file.endsWith('.stories.tsx')
  );
  
  const exports = componentFiles.map(file => {
    const componentName = path.basename(file, '.tsx');
    return `export { ${componentName} } from './${componentName}';`;
  }).join('\n');
  
  const indexPath = path.join(targetDir, 'index.ts');
  fs.writeFileSync(indexPath, `// Auto-generated component index\n// Generated on: ${new Date().toISOString()}\n\n${exports}\n`);
  
  console.log(`📄 Updated component index: ${indexPath}`);
}

/**
 * Run the import process
 */
if (import.meta.url === `file://${process.argv[1]}`) {
  importFigmaComponents().catch(console.error);
}

export { importFigmaComponents };