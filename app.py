#!/usr/bin/env python3
"""
Hugo CMS Companion - A web application for managing Hugo sites
"""

import os
import sys
import json
import subprocess
import shutil
import tempfile
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, Response
import yaml
import frontmatter
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import re
from urllib.parse import unquote
import git  # GitPython for Git operations
from dotenv import load_dotenv  # For .env file support

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Global configuration with environment variable defaults
config = {
    'hugo_repo_path': None,  # Local working directory path
    'hugo_site_built': False,
    'hugo_public_dir': None,
    # Git repository settings from environment variables
    'git_repo_url': os.getenv('HUGO_GIT_REPO_URL'),
    'git_branch': os.getenv('HUGO_GIT_BRANCH', 'main'),
    'git_token': os.getenv('HUGO_GIT_TOKEN'),
    'working_dir': os.getenv('HUGO_WORKING_DIR', '/tmp/hugo-cms-work')
}

class HugoRebuildHandler(FileSystemEventHandler):
    """File system event handler to rebuild Hugo site when content changes"""
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.md'):
            print(f"Content modified: {event.src_path}")
            build_hugo_site()

def load_config(config_file='config.json'):
    """Load application configuration"""
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}

def save_config(config_data, config_file='config.json'):
    """Save application configuration"""
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=2)

def validate_hugo_site(repo_path):
    """Validate that the given path contains a valid Hugo site"""
    if not os.path.exists(repo_path):
        return False, "Repository path does not exist"
    
    config_files = ['config.toml', 'config.yaml', 'config.yml', 'hugo.toml', 'hugo.yaml', 'hugo.yml']
    has_config = any(os.path.exists(os.path.join(repo_path, f)) for f in config_files)
    
    if not has_config:
        return False, "No Hugo configuration file found"
    
    content_dir = os.path.join(repo_path, 'content')
    if not os.path.exists(content_dir):
        return False, "No content directory found"
    
    return True, "Valid Hugo site"

def clear_cached_repo():
    """Clear the cached repository clone"""
    try:
        working_dir = config['working_dir']
        if os.path.exists(working_dir):
            shutil.rmtree(working_dir)
            print(f"Cleared cached repository at {working_dir}")
            return True, "Repository cache cleared"
        return True, "No cached repository to clear"
    except Exception as e:
        return False, f"Error clearing repository cache: {str(e)}"

def setup_git_repo():
    """Clone or update the Git repository"""
    if not config['git_repo_url']:
        return False, "No Git repository URL configured"
    
    try:
        working_dir = config['working_dir']
        repo_dir = os.path.join(working_dir, 'repo')
        
        # Create working directory if it doesn't exist
        os.makedirs(working_dir, exist_ok=True)
        
        # If repo already exists, pull latest changes
        if os.path.exists(repo_dir) and os.path.exists(os.path.join(repo_dir, '.git')):
            repo = git.Repo(repo_dir)
            origin = repo.remotes.origin
            origin.pull(config['git_branch'])
            print(f"Pulled latest changes from {config['git_branch']} branch")
        else:
            # Clone the repository
            if os.path.exists(repo_dir):
                shutil.rmtree(repo_dir)  # Remove any existing non-git directory
            
            # Prepare clone URL with authentication token
            clone_url = config['git_repo_url']
            if config['git_token'] and 'github.com' in clone_url:
                # Insert token for GitHub authentication
                clone_url = clone_url.replace('https://github.com/', f'https://{config["git_token"]}@github.com/')
            
            repo = git.Repo.clone_from(clone_url, repo_dir, branch=config['git_branch'])
            print(f"Cloned repository from {config['git_repo_url']}")
        
        # Update hugo_repo_path to point to our working directory
        config['hugo_repo_path'] = repo_dir
        
        # Validate it's a Hugo site
        valid, message = validate_hugo_site(repo_dir)
        if not valid:
            return False, f"Invalid Hugo site: {message}"
        
        return True, "Git repository setup successfully"
        
    except Exception as e:
        return False, f"Git setup error: {str(e)}"

def commit_and_push_changes(commit_message="Update content via CMS"):
    """Commit local changes and push to remote repository"""
    if not config['hugo_repo_path'] or not os.path.exists(config['hugo_repo_path']):
        return False, "No working directory found"
    
    try:
        repo = git.Repo(config['hugo_repo_path'])
        
        # Check if there are any changes to commit
        if not repo.is_dirty(untracked_files=True):
            return True, "No changes to commit"
        
        # Add all changes
        repo.git.add('.')
        
        # Commit changes
        repo.index.commit(commit_message)
        
        # Push to remote
        origin = repo.remotes.origin
        origin.push(config['git_branch'])
        
        return True, "Changes committed and pushed successfully"
        
    except Exception as e:
        return False, f"Git commit/push error: {str(e)}"

def build_hugo_site():
    """Build the Hugo site"""
    if not config['hugo_repo_path']:
        return False, "No Hugo repository path configured"
    
    if not os.path.exists(config['hugo_repo_path']):
        return False, f"Hugo repository path does not exist: {config['hugo_repo_path']}"
    
    original_cwd = os.getcwd()  # Save current directory outside try block
    
    try:
        # Change to Hugo site directory
        os.chdir(config['hugo_repo_path'])
        
        # Run Hugo build command
        result = subprocess.run(['hugo'], capture_output=True, text=True)
        
        # Restore original directory
        os.chdir(original_cwd)
        
        if result.returncode != 0:
            return False, f"Hugo build failed: {result.stderr}"
        
        # Set public directory path
        config['hugo_public_dir'] = os.path.join(config['hugo_repo_path'], 'public')
        config['hugo_site_built'] = True
        
        print("Hugo site built successfully")
        return True, "Hugo site built successfully"
        
    except Exception as e:
        # Try to restore original directory
        try:
            os.chdir(original_cwd)
        except:
            pass
        return False, f"Build error: {str(e)}"

def get_content_files():
    """Get all markdown content files from Hugo site"""
    if not config['hugo_repo_path']:
        return []
    
    content_dir = os.path.join(config['hugo_repo_path'], 'content')
    if not os.path.exists(content_dir):
        return []
    
    content_files = []
    for root, dirs, files in os.walk(content_dir):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, content_dir)
                content_files.append({
                    'path': file_path,
                    'relative_path': rel_path,
                    'name': file
                })
    
    return content_files

def find_source_file_for_url(url_path):
    """Find the markdown source file that corresponds to a Hugo URL"""
    content_dir = os.path.join(config['hugo_repo_path'], 'content')
    
    # Clean the URL path
    url_path = url_path.strip('/')
    if not url_path:
        url_path = 'index'
    
    # Common patterns Hugo uses for URL to file mapping
    possible_files = [
        f"{url_path}.md",
        f"{url_path}/index.md",
        f"{url_path}/_index.md",
        f"posts/{url_path}.md",
        f"blog/{url_path}.md",
    ]
    
    for possible_file in possible_files:
        full_path = os.path.join(content_dir, possible_file)
        if os.path.exists(full_path):
            return os.path.relpath(full_path, content_dir)
    
    return None

def preserve_frontmatter_format(file_path, new_frontmatter, new_content):
    """Preserve the original frontmatter formatting when updating a file"""
    try:
        # Read the original file to understand its formatting
        with open(file_path, 'r', encoding='utf-8', newline='') as f:
            original_content = f.read()
        
        # Normalize line endings in new content to match original (Unix LF)
        new_content = new_content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Parse the original file to get its structure
        original_post = frontmatter.load(file_path)
        
        # Split the original content to analyze frontmatter formatting
        if original_content.startswith('---\n'):
            parts = original_content.split('---\n', 2)
            if len(parts) >= 3:
                original_fm_raw = parts[1]
                original_body = parts[2] if len(parts) > 2 else ''
                
                # Build new frontmatter while preserving formatting patterns
                new_fm_lines = []
                
                # Create a mapping of original values for comparison
                original_values = {}
                for line in original_fm_raw.split('\n'):
                    if ':' in line:
                        key = line.split(':', 1)[0].strip()
                        value_part = line.split(':', 1)[1]
                        original_values[key] = value_part
                
                # Process each line of original frontmatter to preserve style
                for line in original_fm_raw.split('\n'):
                    if ':' in line:
                        key = line.split(':', 1)[0].strip()
                        if key in new_frontmatter:
                            # Get the original formatting style (quotes, spacing, etc.)
                            original_value_part = line.split(':', 1)[1]
                            has_quotes = '"' in original_value_part
                            # Extract original spacing after colon
                            if original_value_part.lstrip():
                                first_char = original_value_part.lstrip()[0]
                                original_spacing = original_value_part[:original_value_part.find(first_char)]
                            else:
                                original_spacing = ' '
                            
                            # For fields that might get auto-converted (like dates), 
                            # check if the new value is very different from the original
                            new_value = str(new_frontmatter[key])
                            
                            # Special handling for date fields to prevent auto-conversion
                            if key == 'date' and key in original_post.metadata:
                                original_date_value = original_value_part.strip().strip('"')
                                # If the original was a simple date and new value is a verbose date,
                                # keep the original format
                                if len(original_date_value) <= 10 and 'GMT' in new_value:
                                    new_value = original_date_value
                            
                            # Preserve the original formatting style
                            if has_quotes and not (new_value.startswith('"') and new_value.endswith('"')):
                                new_value = f'"{new_value}"'
                            elif not has_quotes and new_value.startswith('"') and new_value.endswith('"'):
                                new_value = new_value[1:-1]
                            
                            new_fm_lines.append(f'{key}:{original_spacing}{new_value}')
                        else:
                            new_fm_lines.append(line)
                    elif line.strip():  # Only include non-empty lines (comments, etc.)
                        new_fm_lines.append(line)
                    # Skip completely empty lines in frontmatter
                
                # Add any new frontmatter keys that weren't in the original
                original_keys = set(original_post.metadata.keys())
                new_keys = set(new_frontmatter.keys())
                for key in new_keys - original_keys:
                    value = str(new_frontmatter[key])
                    # Default to quoted format for strings
                    if isinstance(new_frontmatter[key], str) and not value.isdigit():
                        value = f'"{value}"'
                    new_fm_lines.append(f'{key}: {value}')
                
                # Reconstruct the file with preserved formatting
                new_fm_content = '\n'.join(new_fm_lines)
                result = f'---\n{new_fm_content}\n---\n\n{new_content}'
                
                # Preserve original line ending style (no final newline if original had none)
                if not original_content.endswith('\n'):
                    result = result.rstrip('\n')
                
                # Ensure all line endings are Unix LF
                result = result.replace('\r\n', '\n').replace('\r', '\n')
                
                return result
        
        # Fallback to frontmatter.dumps if parsing fails
        post = frontmatter.Post(new_content, **new_frontmatter)
        return frontmatter.dumps(post)
    
    except Exception as e:
        # Fallback to frontmatter.dumps if anything goes wrong
        post = frontmatter.Post(new_content, **new_frontmatter)
        return frontmatter.dumps(post)

def get_content_type(file_path):
    """Get the appropriate MIME type for a file based on its extension"""
    extension = os.path.splitext(file_path)[1].lower()
    
    content_types = {
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.txt': 'text/plain',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
        '.ttf': 'font/ttf',
        '.otf': 'font/otf',
        '.eot': 'application/vnd.ms-fontobject',
        '.pdf': 'application/pdf',
        '.zip': 'application/zip',
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
    }
    
    return content_types.get(extension, 'application/octet-stream')

def is_binary_file(file_path):
    """Check if a file should be treated as binary"""
    # Check if it's a directory first
    if os.path.isdir(file_path):
        return False  # Directories are not binary files
    
    extension = os.path.splitext(file_path)[1].lower()
    
    text_extensions = {'.html', '.css', '.js', '.json', '.xml', '.txt', '.svg', '.md'}
    binary_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.woff', '.woff2', 
                        '.ttf', '.otf', '.eot', '.pdf', '.zip', '.mp4', '.webm', '.mp3', '.wav'}
    
    if extension in text_extensions:
        return False
    elif extension in binary_extensions:
        return True
    else:
        # For unknown extensions, try to detect if it's binary
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)  # Try to read first 1KB as text
            return False
        except (UnicodeDecodeError, UnicodeError, IsADirectoryError):
            return True

def inject_admin_controls(html_content, source_file=None):
    """Inject admin controls into HTML content"""
    admin_css = '''
<style>
.hugo-cms-admin {
    position: fixed;
    top: 10px;
    right: 10px;
    z-index: 9999;
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 10px;
    border-radius: 5px;
    font-family: Arial, sans-serif;
    font-size: 14px;
}
.hugo-cms-admin button {
    background: #007cba;
    color: white;
    border: none;
    padding: 8px 12px;
    margin: 2px;
    border-radius: 3px;
    cursor: pointer;
}
.hugo-cms-admin button:hover {
    background: #005a87;
}
.hugo-cms-modal {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    z-index: 10000;
}
.hugo-cms-modal-content {
    background: white;
    margin: 5% auto;
    padding: 20px;
    width: 80%;
    max-width: 800px;
    border-radius: 5px;
    max-height: 80vh;
    overflow-y: auto;
}
.hugo-cms-close {
    float: right;
    font-size: 28px;
    font-weight: bold;
    cursor: pointer;
}
.hugo-cms-form textarea {
    width: 100%;
    height: 300px;
    margin: 10px 0;
}
.hugo-cms-form input[type="text"], .hugo-cms-form input[type="date"] {
    width: 100%;
    padding: 8px;
    margin: 5px 0;
    border: 1px solid #ddd;
    border-radius: 3px;
}
</style>
'''
    
    admin_controls = f'''
<div class="hugo-cms-admin">
    <div>Hugo CMS</div>
    {f'<button onclick="editCurrentPage()" title="Edit this page">✏️ Edit</button>' if source_file else ''}
    <button onclick="createNewPage()" title="Create new page">➕ New</button>
    <button onclick="rebuildSite()" title="Rebuild site">🔄 Build</button>
    <button onclick="publishChanges()" title="Publish to Git repository">🚀 Publish</button>
    <button onclick="clearCache()" title="Clear repository cache and re-clone">🗑️ Clear Cache</button>
</div>
'''
    
    admin_js = f'''
<script>
let currentSourceFile = '{source_file or ''}';

function editCurrentPage() {{
    if (!currentSourceFile) {{
        alert('No source file found for this page');
        return;
    }}
    
    fetch(`/admin/api/get-content/${{encodeURIComponent(currentSourceFile)}}`)
        .then(response => response.json())
        .then(data => {{
            if (data.success) {{
                showEditModal(data.frontmatter, data.content, currentSourceFile);
            }} else {{
                alert('Error loading content: ' + data.message);
            }}
        }});
}}

function createNewPage() {{
    showEditModal({{}}, '', null);
}}

function showEditModal(frontmatter, content, filePath) {{
    const modal = document.getElementById('hugo-cms-modal') || createModal();
    
    let frontmatterFields = '';
    const commonFields = ['title', 'date', 'draft', 'tags', 'categories'];
    
    // Add existing frontmatter fields
    for (const [key, value] of Object.entries(frontmatter)) {{
        frontmatterFields += `
            <div>
                <label>${{key}}:</label>
                <input type="text" name="fm_${{key}}" value="${{value}}" />
            </div>
        `;
    }}
    
    // Add common fields if not present
    for (const field of commonFields) {{
        if (!frontmatter.hasOwnProperty(field)) {{
            const inputType = field === 'date' ? 'date' : 'text';
            frontmatterFields += `
                <div>
                    <label>${{field}}:</label>
                    <input type="${{inputType}}" name="fm_${{field}}" value="" />
                </div>
            `;
        }}
    }}
    
    modal.innerHTML = `
        <div class="hugo-cms-modal-content">
            <span class="hugo-cms-close" onclick="closeModal()">&times;</span>
            <h2>${{filePath ? 'Edit Page' : 'Create New Page'}}</h2>
            <form class="hugo-cms-form" onsubmit="savePage(event, '${{filePath || ''}}')">
                ${{!filePath ? `
                    <div>
                        <label>File Path:</label>
                        <input type="text" name="filename" placeholder="news/recent-news-item.md" required />
                    </div>
                ` : ''}}
                
                <h3>Frontmatter</h3>
                ${{frontmatterFields}}
                
                <h3>Content</h3>
                <textarea name="content" placeholder="Write your content here...">${{content}}</textarea>
                
                <button type="submit">${{filePath ? 'Save Changes' : 'Create Page'}}</button>
            </form>
        </div>
    `;
    
    modal.style.display = 'block';
}}

function createModal() {{
    const modal = document.createElement('div');
    modal.id = 'hugo-cms-modal';
    modal.className = 'hugo-cms-modal';
    document.body.appendChild(modal);
    return modal;
}}

function closeModal() {{
    const modal = document.getElementById('hugo-cms-modal');
    if (modal) modal.style.display = 'none';
}}

function savePage(event, filePath) {{
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    
    const url = filePath ? 
        `/admin/api/save/${{encodeURIComponent(filePath)}}` : 
        '/admin/api/create';
    
    fetch(url, {{
        method: 'POST',
        body: formData
    }})
    .then(response => response.json())
    .then(data => {{
        if (data.success) {{
            alert(data.message);
            closeModal();
            
            // If this is a new page creation, navigate to the new page
            if (!filePath && data.url) {{
                setTimeout(() => window.location.href = data.url, 1000);
            }} else {{
                // For edits, reload the current page
                setTimeout(() => location.reload(), 1000);
            }}
        }} else {{
            alert('Error: ' + data.message);
        }}
    }})
    .catch(error => {{
        alert('Error: ' + error.message);
    }});
}}

function rebuildSite() {{
    fetch('/admin/api/build')
        .then(response => response.json())
        .then(data => {{
            alert(data.message);
            if (data.success) {{
                setTimeout(() => location.reload(), 1000);
            }}
        }});
}}

function publishChanges() {{
    if (!confirm('Are you sure you want to publish all changes to the Git repository?')) {{
        return;
    }}
    
    fetch('/admin/api/publish', {{
        method: 'POST'
    }})
    .then(response => response.json())
    .then(data => {{
        alert(data.message);
    }})
    .catch(error => {{
        alert('Error: ' + error.message);
    }});
}}

function clearCache() {{
    if (!confirm('Are you sure you want to clear the repository cache and re-clone? This will discard any uncommitted local changes.')) {{
        return;
    }}
    
    fetch('/admin/api/clear-cache', {{
        method: 'POST'
    }})
    .then(response => response.json())
    .then(data => {{
        alert(data.message);
        if (data.success) {{
            setTimeout(() => location.reload(), 1000);
        }}
    }})
    .catch(error => {{
        alert('Error: ' + error.message);
    }});
}}

// Close modal when clicking outside
window.onclick = function(event) {{
    const modal = document.getElementById('hugo-cms-modal');
    if (event.target == modal) {{
        closeModal();
    }}
}}
</script>
'''    
    
    # Inject CSS in head
    html_content = re.sub(r'</head>', admin_css + '</head>', html_content, flags=re.IGNORECASE)
    
    # Inject admin controls and JS before closing body tag
    html_content = re.sub(r'</body>', admin_controls + admin_js + '</body>', html_content, flags=re.IGNORECASE)
    
    return html_content

@app.route('/')
def index():
    """Serve Hugo site index with admin controls"""
    if not config.get('git_repo_url') or not config.get('hugo_repo_path'):
        return setup_page()
    
    return serve_hugo_page('/')

def setup_page():
    """Show setup page for configuring Hugo repository"""
    # Check if environment variables are already configured
    has_env_config = bool(config.get('git_repo_url') and config.get('git_token'))
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>Hugo CMS Setup</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 700px; margin: 50px auto; padding: 20px; }}
        input[type="text"], input[type="password"] {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }}
        button {{ background: #007cba; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }}
        .secondary-btn {{ background: #666; }}
        .error {{ color: red; margin: 10px 0; }}
        .success {{ color: green; margin: 10px 0; font-weight: bold; }}
        .form-group {{ margin: 15px 0; }}
        label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        .help-text {{ font-size: 12px; color: #666; margin-top: 5px; }}
        .env-config {{ background: #f0f8ff; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #007cba; }}
        .manual-config {{ background: #fff8dc; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffa500; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; font-size: 14px; }}
        .toggle-section {{ cursor: pointer; padding: 10px; background: #f8f9fa; border-radius: 5px; margin: 10px 0; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <h1>Hugo CMS Setup</h1>
    
    {'<div class="success">✅ Environment variables detected! Repository is ready.</div>' if has_env_config else ''}
    
    <div class="env-config">
        <h2>📁 Recommended: Environment Variables (.env file)</h2>
        <p>Create a <code>.env</code> file in this directory with your repository configuration:</p>
        <pre># Hugo CMS Configuration
HUGO_GIT_REPO_URL=https://github.com/yourusername/your-hugo-site.git
HUGO_GIT_BRANCH=main
HUGO_GIT_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
HUGO_WORKING_DIR=/tmp/hugo-cms-work</pre>
        <p><strong>Benefits:</strong> Secure, version-controllable (add .env to .gitignore), easy deployment</p>
        {'<button onclick="location.reload()" class="secondary-btn">🔄 Refresh</button>' if not has_env_config else ''}
        {'<button onclick="setupFromEnv()">🚀 Setup from Environment</button>' if has_env_config else ''}
    </div>
    
    <div class="toggle-section" onclick="toggleManualConfig()">
        <h2>⚙️ Alternative: Manual Configuration (Click to expand)</h2>
    </div>
    
    <div id="manual-config" class="manual-config hidden">
        <p><strong>Warning:</strong> This method exposes credentials in the browser. Use only for testing.</p>
        
        <form onsubmit="setupRepo(event)">
            <div class="form-group">
                <label for="git_repo_url">Git Repository URL:</label>
                <input type="text" id="git_repo_url" placeholder="https://github.com/username/hugo-site.git" required>
                <div class="help-text">GitHub, GitLab, or any Git repository URL</div>
            </div>
            
            <div class="form-group">
                <label for="git_branch">Branch:</label>
                <input type="text" id="git_branch" placeholder="main" value="main" required>
                <div class="help-text">Which branch to work with</div>
            </div>
            
            <div class="form-group">
                <label for="git_token">Access Token:</label>
                <input type="password" id="git_token" placeholder="ghp_xxxxxxxxxxxx">
                <div class="help-text">GitHub Personal Access Token or similar credential</div>
            </div>
            
            <button type="submit">Setup Repository</button>
        </form>
    </div>
    
    <div id="error" class="error"></div>
    
    <script>
    function toggleManualConfig() {{
        const manualConfig = document.getElementById('manual-config');
        manualConfig.classList.toggle('hidden');
    }}
    
    function setupFromEnv() {{
        const errorDiv = document.getElementById('error');
        
        fetch('/setup', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json'
            }},
            body: JSON.stringify({{'use_env': true}})
        }})
        .then(response => response.json())
        .then(data => {{
            if (data.success) {{
                location.reload();
            }} else {{
                errorDiv.textContent = data.message;
            }}
        }})
        .catch(error => {{
            errorDiv.textContent = 'Error: ' + error.message;
        }});
    }}
    
    function setupRepo(event) {{
        event.preventDefault();
        const gitRepoUrl = document.getElementById('git_repo_url').value;
        const gitBranch = document.getElementById('git_branch').value;
        const gitToken = document.getElementById('git_token').value;
        const errorDiv = document.getElementById('error');
        
        const formData = new FormData();
        formData.append('git_repo_url', gitRepoUrl);
        formData.append('git_branch', gitBranch);
        formData.append('git_token', gitToken);
        
        // Show loading state
        event.target.querySelector('button').textContent = 'Setting up...';
        event.target.querySelector('button').disabled = true;
        
        fetch('/setup', {{
            method: 'POST',
            body: formData
        }})
        .then(response => response.json())
        .then(data => {{
            if (data.success) {{
                location.reload();
            }} else {{
                errorDiv.textContent = data.message;
                event.target.querySelector('button').textContent = 'Setup Repository';
                event.target.querySelector('button').disabled = false;
            }}
        }})
        .catch(error => {{
            errorDiv.textContent = 'Error: ' + error.message;
            event.target.querySelector('button').textContent = 'Setup Repository';
            event.target.querySelector('button').disabled = false;
        }});
    }}
    </script>
</body>
</html>
    '''

def serve_hugo_page(url_path):
    """Serve Hugo page with admin controls injected"""
    if not config['hugo_site_built']:
        success, message = build_hugo_site()
        if not success:
            return f"<h1>Build Error</h1><p>{message}</p>", 500
    
    # Handle root path
    if url_path == '/':
        file_path = 'index.html'
    else:
        file_path = url_path.strip('/')
    
    full_path = os.path.join(config['hugo_public_dir'], file_path)
    
    # If direct path doesn't exist, try alternative paths for HTML content
    if not os.path.exists(full_path):
        # For HTML content, try Hugo's pretty URL patterns
        if not any(file_path.endswith(ext) for ext in ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.otf', '.eot']):
            alternatives = [
                os.path.join(config['hugo_public_dir'], file_path + '.html'),
                os.path.join(config['hugo_public_dir'], file_path, 'index.html'),
                os.path.join(config['hugo_public_dir'], file_path + '/index.html')
            ]
            
            for alt_path in alternatives:
                if os.path.exists(alt_path):
                    full_path = alt_path
                    break
            else:
                return "Page not found", 404
        else:
            # For static assets, return 404 if not found
            return "Asset not found", 404
    
    # If the path is a directory, try to serve index.html from it
    if os.path.isdir(full_path):
        index_path = os.path.join(full_path, 'index.html')
        if os.path.exists(index_path):
            full_path = index_path
        else:
            return "Page not found", 404
    
    # Determine content type based on file extension
    content_type = get_content_type(full_path)
    
    # For binary files, read in binary mode
    if is_binary_file(full_path):
        try:
            with open(full_path, 'rb') as f:
                file_content = f.read()
            return Response(file_content, mimetype=content_type)
        except Exception as e:
            return f"Error reading binary file: {e}", 500
    
    # For text files, read in text mode
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
    except Exception as e:
        return f"Error reading file: {e}", 500
    
    # Only inject admin controls for HTML files
    if full_path.endswith('.html'):
        # Find corresponding source file
        source_file = find_source_file_for_url(url_path)
        
        # Inject admin controls
        file_content = inject_admin_controls(file_content, source_file)
    
    return Response(file_content, mimetype=content_type)

@app.route('/setup', methods=['POST'])
def setup():
    """Setup Git repository configuration"""
    # Check if this is a request to use environment variables
    if request.is_json:
        data = request.get_json()
        if data.get('use_env'):
            # Validate environment variables are present
            if not config.get('git_repo_url'):
                return jsonify({'success': False, 'message': 'HUGO_GIT_REPO_URL environment variable is required'})
            if not config.get('git_token'):
                return jsonify({'success': False, 'message': 'HUGO_GIT_TOKEN environment variable is required'})
            
            # Setup (clone/pull) the Git repository using env vars
            success, message = setup_git_repo()
            if not success:
                return jsonify({'success': False, 'message': message})
            
            return jsonify({'success': True, 'message': 'Git repository configured from environment variables'})
    
    # Handle manual form submission
    git_repo_url = request.form.get('git_repo_url')
    git_branch = request.form.get('git_branch', 'main')
    git_token = request.form.get('git_token', '')
    
    if not git_repo_url:
        return jsonify({'success': False, 'message': 'Git repository URL is required'})
    
    # Save Git configuration (override environment variables)
    config['git_repo_url'] = git_repo_url
    config['git_branch'] = git_branch
    config['git_token'] = git_token
    
    # Setup (clone/pull) the Git repository
    success, message = setup_git_repo()
    if not success:
        return jsonify({'success': False, 'message': message})
    
    # Save configuration to file (for manual config persistence)
    save_config(config)
    
    return jsonify({'success': True, 'message': 'Git repository configured successfully'})

# API Routes for admin functionality
@app.route('/admin/api/build')
def api_build():
    """API endpoint to build Hugo site"""
    success, message = build_hugo_site()
    return jsonify({'success': success, 'message': message})

@app.route('/admin/api/publish', methods=['POST'])
def api_publish():
    """API endpoint to publish changes to Git repository"""
    # First, pull any remote changes to avoid conflicts
    pull_success, pull_message = setup_git_repo()
    if not pull_success:
        return jsonify({'success': False, 'message': f'Failed to pull latest changes: {pull_message}'})
    
    # Commit and push local changes
    success, message = commit_and_push_changes()
    return jsonify({'success': success, 'message': message})

@app.route('/admin/api/clear-cache', methods=['POST'])
def api_clear_cache():
    """API endpoint to clear the repository cache and re-clone"""
    try:
        # Clear the cached repository
        clear_success, clear_message = clear_cached_repo()
        if not clear_success:
            return jsonify({'success': False, 'message': clear_message})
        
        # Reset hugo_repo_path to avoid stale references
        config['hugo_repo_path'] = None
        config['hugo_site_built'] = False
        config['hugo_public_dir'] = None
        
        # Re-setup the repository
        setup_success, setup_message = setup_git_repo()
        if not setup_success:
            return jsonify({'success': False, 'message': f'Cache cleared but failed to re-clone: {setup_message}'})
        
        # Rebuild the site after re-cloning
        build_success, build_message = build_hugo_site()
        if not build_success:
            return jsonify({'success': False, 'message': f'Re-cloned successfully but build failed: {build_message}'})
        
        return jsonify({'success': True, 'message': 'Repository cache cleared, re-cloned, and rebuilt successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Cache clear error: {str(e)}'})

@app.route('/admin/api/get-content/<path:file_path>')
def api_get_content(file_path):
    """API endpoint to get markdown file content"""
    full_path = os.path.join(config['hugo_repo_path'], 'content', file_path)
    
    if not os.path.exists(full_path):
        return jsonify({'success': False, 'message': 'File not found'})
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        
        return jsonify({
            'success': True,
            'frontmatter': post.metadata,
            'content': post.content
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/api/save/<path:file_path>', methods=['POST'])
def api_save_file(file_path):
    """API endpoint to save changes to a markdown file"""
    full_path = os.path.join(config['hugo_repo_path'], 'content', file_path)
    
    try:
        frontmatter_data = {}
        for key, value in request.form.items():
            if key.startswith('fm_') and value.strip():
                fm_key = key[3:]  # Remove 'fm_' prefix
                frontmatter_data[fm_key] = value.strip()
        
        content = request.form.get('content', '')
        
        # Use the formatting preservation function to maintain original style
        formatted_content = preserve_frontmatter_format(full_path, frontmatter_data, content)
        
        # Write back to file with Unix line endings
        with open(full_path, 'wb') as f:
            f.write(formatted_content.encode('utf-8'))
        
        # Rebuild site
        build_hugo_site()
        
        return jsonify({'success': True, 'message': 'File saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/admin/api/create', methods=['POST'])
def api_create_file():
    """API endpoint to create a new markdown file"""
    try:
        filename = request.form.get('filename')
        if not filename:
            return jsonify({'success': False, 'message': 'Filename is required'})
        
        if not filename.endswith('.md'):
            filename += '.md'
        
        # Create path in content directory
        full_path = os.path.join(config['hugo_repo_path'], 'content', filename)
        
        # Check if file already exists
        if os.path.exists(full_path):
            return jsonify({'success': False, 'message': 'File already exists'})
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Prepare frontmatter
        frontmatter_data = {}
        for key, value in request.form.items():
            if key.startswith('fm_') and value.strip():
                fm_key = key[3:]  # Remove 'fm_' prefix
                frontmatter_data[fm_key] = value.strip()
        
        content = request.form.get('content', '')
        
        # Create new post
        post = frontmatter.Post(content, **frontmatter_data)
        
        # Write to file with Unix line endings
        with open(full_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(frontmatter.dumps(post))
        
        # Rebuild site
        build_hugo_site()
        
        # Generate the URL for the new page
        # Remove .md extension and create proper Hugo URL
        url_path = filename.replace('.md', '')
        if not url_path.startswith('/'):
            url_path = '/' + url_path
        
        return jsonify({
            'success': True, 
            'message': f'File {filename} created successfully',
            'url': url_path
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

# Catch-all route to serve Hugo pages
@app.route('/<path:path>')
def serve_hugo_content(path):
    """Serve any Hugo page with admin controls injected"""
    return serve_hugo_page('/' + path)

if __name__ == '__main__':
    # Load existing configuration
    saved_config = load_config()
    config.update(saved_config)
    
    # If Git repository is configured, set it up
    if config.get('git_repo_url'):
        print(f"Setting up Git repository: {config['git_repo_url']}")
        
        # Clear any existing cached repository on startup
        clear_success, clear_message = clear_cached_repo()
        if not clear_success:
            print(f"Warning: {clear_message}")
        
        success, message = setup_git_repo()
        if success:
            print(f"Git repository ready: {message}")
        else:
            print(f"Git setup warning: {message}")
    
    # Set up file watcher if Hugo repo is configured
    if config.get('hugo_repo_path'):
        content_dir = os.path.join(config['hugo_repo_path'], 'content')
        if os.path.exists(content_dir):
            event_handler = HugoRebuildHandler()
            observer = Observer()
            observer.schedule(event_handler, content_dir, recursive=True)
            observer.start()
    
    print("Hugo CMS Companion starting...")
    print(f"Access the application at: http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
