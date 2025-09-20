# Hugo CMS

A web-based content management system for Hugo static sites with Git integration.

## Features

- 📝 **Live Content Editing**: Edit Hugo content directly in the browser
- 🔧 **Admin Controls**: Overlay controls on any Hugo page for instant editing
- 🚀 **Git Integration**: Automatic commit and push to remote repositories
- ⚡ **Live Reload**: Auto-rebuild and refresh when content changes
- 🎯 **Format Preservation**: Maintains original frontmatter formatting
- 🔒 **Secure Configuration**: Environment variable-based setup

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Repository (Recommended: Environment Variables)

Create a `.env` file in the project directory:

```bash
cp .env.example .env
```

Edit `.env` with your repository settings:

```env
# Hugo CMS Configuration
HUGO_GIT_REPO_URL=https://github.com/yourusername/your-hugo-site.git
HUGO_GIT_BRANCH=main
HUGO_GIT_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
HUGO_WORKING_DIR=/tmp/hugo-cms-work
```

**How to get a GitHub Token:**
1. Go to [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. Generate a new token with `repo` permissions
3. Copy the token to `HUGO_GIT_TOKEN` in your `.env` file

### 3. Run the Application

```bash
python3 app.py
```

Open http://localhost:5000 in your browser.

### 4. Usage

- **Edit Pages**: Click the ✏️ Edit button on any page
- **Create Pages**: Click the ➕ New button  
- **Build Site**: Click the 🔄 Build button to regenerate
- **Publish**: Click the 🚀 Publish button to commit and push changes

## Configuration Options

### Environment Variables (Recommended)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HUGO_GIT_REPO_URL` | ✅ | - | Git repository URL |
| `HUGO_GIT_BRANCH` | ❌ | `main` | Git branch to use |
| `HUGO_GIT_TOKEN` | ✅ | - | Git access token |
| `HUGO_WORKING_DIR` | ❌ | `/tmp/hugo-cms-work` | Local working directory |

### Manual Configuration

If environment variables aren't configured, the setup page will allow manual entry. **Note**: This method exposes credentials in the browser and should only be used for testing.

## Security

- 🔒 **Environment Variables**: Keep sensitive tokens out of your code
- 🙈 **Git Ignore**: `.env` files are automatically ignored by Git
- 🔐 **Token Permissions**: Use tokens with minimal required permissions

## Development

### Requirements

- Python 3.7+
- Git
- Hugo (installed and in PATH)

### Project Structure

```
hugo-cms/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── .env.example       # Environment variables template
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

### Production Deployment

1. Clone this repository to your server
2. Configure `.env` with your production settings
3. Use a production WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## License

MIT License - see LICENSE file for details.
