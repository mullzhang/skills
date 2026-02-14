---
name: file-organizer
description: Intelligently organize messy directories by analyzing files and grouping them based on AI content analysis, temporal patterns, and metadata. Use when users want to clean up cluttered folders (Downloads, Desktop, Documents), sort files by project or topic, or automatically categorize files. Triggers include requests like "organize this folder", "clean up my Downloads", "group these files by project", or "sort my desktop files".
---

# File Organizer

Automatically analyze and organize files in directories using AI-powered content analysis, temporal clustering, and metadata examination.

## Overview

This skill helps organize cluttered directories by:
1. Analyzing file metadata (creation dates, modification times, sizes, extensions)
2. Detecting temporal clusters (files modified in sequence, likely related to same project)
3. Using AI to analyze file names and content for semantic grouping
4. Generating organization proposals for user approval
5. Moving files into organized directory structure

## Workflow

### Step 1: Analyze the Directory

Run the analysis script to collect file metadata:

```bash
python scripts/analyze_files.py <directory-path> [-r] [-t TIME_THRESHOLD]
```

**Arguments:**
- `<directory-path>`: Path to directory (e.g., ~/Downloads, ~/Desktop)
- `-r, --recursive`: Include subdirectories
- `-t, --time-threshold`: Seconds for temporal clustering (default: 3600 = 1 hour)
- `-o, --output`: Save analysis to JSON file

**Example:**
```bash
# Analyze Downloads folder with 24-hour clustering threshold
python scripts/analyze_files.py ~/Downloads -t 86400 -o analysis.json
```

The script outputs comprehensive analysis including:
- Total file count and size
- File type distribution
- Temporal clusters (files modified close in time)
- Detailed metadata for each file

### Step 2: Generate Grouping Proposal

Based on the analysis, create a grouping proposal using AI reasoning. Consider:

**Temporal Clusters**: Files in the same cluster were likely worked on together (same project/task).

**File Names**: Extract semantic meaning from names:
- Project names, client names, dates
- Keywords indicating purpose (invoice, receipt, screenshot, report)
- Naming patterns suggesting relationships

**Modification Patterns**:
- Files updated on same day → likely related
- Sequential updates → workflow or iteration
- Large gaps → different projects/contexts

**Content Analysis** (when applicable):
- Document topics and themes
- Image subjects
- Code project structure

Create a grouping plan with structure:
```json
{
  "base_directory": "/path/to/organized",
  "groups": {
    "GroupName": {
      "description": "Brief description of this group",
      "files": ["/path/to/file1", "/path/to/file2"]
    }
  }
}
```

**Grouping Strategies:**

- **By Project/Topic**: Files related to same project or subject matter
- **By Date**: Monthly or yearly folders (e.g., "2024-01", "2025-Q4")
- **By Type with Context**: Not just "Documents" but "Work Documents", "Personal Documents"
- **By Temporal Cluster**: Use cluster_id from analysis to group sequential work

**Example Groups:**
- "ProjectX_Design" - Screenshots and design files from project X
- "Receipts_2024" - All receipts from 2024
- "Client_ABC_Invoices" - Invoices for specific client
- "Personal_Photos_December" - Personal photos from December

### Step 3: Present Proposal to User

Before executing, always present the proposal clearly:

```
I've analyzed the directory and found [N] files. Here's my organization proposal:

**Group 1: [Name]** ([N] files)
Description: [Why these files belong together]
Files: [file1, file2, ...]

**Group 2: [Name]** ([N] files)
Description: [Why these files belong together]
Files: [file1, file2, ...]

This will create organized subdirectories under: [base_directory]

Shall I proceed with this organization?
```

### Step 4: Execute Organization

Once approved, save the grouping plan as JSON and execute:

```bash
python scripts/organize_files.py plan.json [-n] [-c]
```

**Arguments:**
- `plan.json`: The grouping plan file
- `-n, --dry-run`: Preview without moving files
- `-c, --copy`: Copy files instead of moving
- `-o, --output`: Save results to JSON

**Recommended Workflow:**
1. First run with `--dry-run` to preview
2. If user approves, run without dry-run to execute
3. Use `--copy` if user wants to keep originals

**Example:**
```bash
# Preview the organization
python scripts/organize_files.py plan.json --dry-run

# Execute (move files)
python scripts/organize_files.py plan.json

# Or copy instead of move
python scripts/organize_files.py plan.json --copy
```

## Best Practices

**Analysis:**
- Use longer time thresholds (12-24 hours) for personal files
- Use shorter thresholds (1-2 hours) for work files with focused sessions
- Always run recursive analysis on Desktop (many nested folders)

**Grouping:**
- Aim for 3-10 groups (not too granular, not too broad)
- Name groups descriptively (avoid generic names like "Group1", "Misc")
- Provide clear descriptions explaining the grouping logic
- Leave obviously organized files (already in subdirectories) alone

**User Interaction:**
- Always present proposal before executing
- Explain the reasoning behind groupings
- Offer to refine if user disagrees with groupings
- Default to dry-run first for safety

**Safety:**
- Never organize system directories or hidden files
- Respect existing directory structures within target folder
- Handle filename conflicts gracefully (append counter)
- Preserve file timestamps and permissions

## Common Usage Patterns

**Pattern 1: Quick Desktop Cleanup**
```
User: "Clean up my Desktop"
1. Run analysis on ~/Desktop with recursive
2. Group by temporal clusters and semantic meaning
3. Present proposal with 5-8 logical groups
4. Execute with dry-run, then real move
```

**Pattern 2: Monthly Download Organization**
```
User: "Organize last month's downloads"
1. Run analysis filtering by date
2. Group by file type with context (work docs, personal, media)
3. Create monthly subfolder structure
4. Execute organization
```

**Pattern 3: Project-Based Sorting**
```
User: "Sort these files by project"
1. Analyze file names for project indicators
2. Use temporal clustering to identify project sessions
3. Group by detected project names
4. Present proposal highlighting how projects were identified
```

## Handling Edge Cases

**Duplicate Names**: Script automatically appends counter (file_1.txt, file_2.txt)

**Large Directories**: For 500+ files, consider:
- Breaking into smaller batches
- Using more specific grouping criteria
- Offering iterative organization

**Mixed Content**: When files don't fit clear groups:
- Create "Review" group for ambiguous files
- Allow user to manually categorize later
- Use broader categories (by date or type)

**Already Organized**: Skip files already in logical subdirectories

## Scripts Reference

**scripts/analyze_files.py**
- Collects file metadata and statistics
- Performs temporal clustering analysis
- Outputs JSON with comprehensive file information

**scripts/organize_files.py**
- Executes grouping plan by moving/copying files
- Handles conflicts and errors gracefully
- Provides detailed progress output and summary
