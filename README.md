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

#### Option A: Docker (Recommended for Development)

Docker ensures your local environment matches the production Railway deployment exactly.

```bash
# Easy way - use the provided script
./run-local.sh

# Or manually:
docker build -t hugo-cms .
docker run -d --name hugo-cms-dev -p 5000:5000 \
  -e GIT_PYTHON_REFRESH=quiet \
  -v hugo_cms_data:/tmp/hugo-cms-work \
  hugo-cms

# View logs
docker logs -f hugo-cms-dev

# Stop when done
docker stop hugo-cms-dev && docker rm hugo-cms-dev
```

#### Option B: Direct Python (Alternative)

```bash
# Requires Hugo and Git installed locally
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

### Branch-Based Security (Recommended)
- 🌿 **Default Branch**: The CMS defaults to the `cms-beta` branch instead of `main`
- 🏭 **Production Isolation**: Changes are committed to `cms-beta`, keeping production (`main`) safe
- 👀 **Review Process**: Review changes in `cms-beta` before merging to `main`
- 🛡️ **Branch Protection**: Set up GitHub branch protection rules for `main` (see `GITHUB_TOKEN_SETUP.md`)

### Access Controls & Monitoring
- 🔒 **Environment Variables**: Keep sensitive tokens out of your code
- 🙈 **Git Ignore**: `.env` files are automatically ignored by Git
- 🔐 **Fine-Grained Tokens**: Use GitHub fine-grained tokens with minimal permissions (see `GITHUB_TOKEN_SETUP.md`)
- 📊 **Security Logging**: All file modifications and git pushes are logged with IP addresses
- 🔄 **Token Rotation**: Regularly rotate GitHub tokens

## Development

### Requirements

#### Docker Development (Recommended)
- Docker and Docker CLI
- Git (for version control)

#### Direct Python Development (Alternative)
- Python 3.7+
- Git
- Hugo (installed and in PATH)

### Docker Development Workflow

```bash
# 1. Make code changes
vim app.py

# 2. Test changes
./run-local.sh

# 3. View logs and test functionality
docker logs -f hugo-cms-dev

# 4. Stop container when done
docker stop hugo-cms-dev && docker rm hugo-cms-dev

# 5. Commit and deploy
git add -A
git commit -m "Your changes"
git push  # Triggers Railway deployment
```

### Project Structure

```
hugo-cms/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── Dockerfile               # Docker container configuration
├── run-local.sh             # Local development script
├── .env.example             # Environment variables template
├── GITHUB_TOKEN_SETUP.md    # Security setup guide
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

### Docker Troubleshooting

```bash
# Container won't start?
docker logs hugo-cms-dev

# Port already in use?
docker ps  # Check for existing containers
docker stop hugo-cms-dev && docker rm hugo-cms-dev

# Clean rebuild after code changes
docker build --no-cache -t hugo-cms .

# Access container shell for debugging
docker exec -it hugo-cms-dev /bin/bash

# Remove all hugo-cms containers and images
docker ps -a | grep hugo-cms | awk '{print $1}' | xargs docker rm -f
docker images | grep hugo-cms | awk '{print $3}' | xargs docker rmi -f
```

### Production Deployment

#### Secure Deployment (Railway + Cloudflare + Netlify DNS)

1. **Deploy to Railway:**
   ```bash
   railway login
   railway init
   railway up
   ```

2. **Configure Custom Domain:**
   - Railway Dashboard → Add Domain: `cms.yourdomain.com`

3. **Setup Cloudflare:**
   - Add `yourdomain.com` to Cloudflare (free plan)
   - DNS Record: `CNAME cms → your-app.railway.app` (proxied 🧡)
   - Security → IP Access Rules → Whitelist editor IPs

4. **Update Netlify DNS:**
   - Add: `CNAME cms → cms.yourdomain.com.cdn.cloudflare.net`

5. **Secure Railway Access:**
   - Add to Railway environment: `HUGO_ALLOWED_DOMAINS=cms.yourdomain.com`
   - This blocks direct Railway URL access, forcing traffic through Cloudflare

**Result:** `https://cms.yourdomain.com` accessible only to whitelisted IPs

#### Alternative: Simple Deployment

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## License

MIT License - see LICENSE file for details.
