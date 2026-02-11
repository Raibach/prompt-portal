# Local Database Setup Guide

## Current Status

### ❌ Issues Found

1. **DATABASE_URL is NOT SET**
   - No `.env` file found
   - Environment variables not configured

2. **PostgreSQL Not Detected**
   - PostgreSQL client (`psql`) not in PATH
   - PostgreSQL server not running or not accessible

3. **Dependencies Missing**
   - `psycopg2-binary` not installed (required for PostgreSQL connection)

---

## Setup Instructions

### Step 1: Install PostgreSQL

#### macOS (using Homebrew)
```bash
# Install PostgreSQL
brew install postgresql@15

# Start PostgreSQL service
brew services start postgresql@15

# Add to PATH (add to ~/.zshrc or ~/.bash_profile)
echo 'export PATH="/opt/homebrew/opt/postgresql@15/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### Alternative: PostgreSQL.app (macOS GUI)
1. Download from: https://postgresapp.com/
2. Install and launch the app
3. Click "Initialize" to create a new server
4. Default port: 5432

#### Verify Installation
```bash
# Check if PostgreSQL is running
pg_isready -h localhost -p 5432

# Should output: localhost:5432 - accepting connections
```

### Step 2: Create Database

```bash
# Connect to PostgreSQL (default user is your macOS username)
psql postgres

# Or if you set a password:
psql -U postgres -h localhost
```

Once connected, run:
```sql
-- Create database
CREATE DATABASE grace_db;

-- Create user (optional, or use your macOS user)
CREATE USER grace_user WITH PASSWORD 'your_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE grace_db TO grace_user;

-- Exit psql
\q
```

### Step 3: Install Python Dependencies

```bash
cd /Users/raibach/Documents/development/grace-editor

# Install all dependencies (includes psycopg2-binary)
pip3 install -r requirements.txt

# Or install just the database driver
pip3 install psycopg2-binary python-dotenv
```

### Step 4: Create .env File

Create a `.env` file in the project root:

```bash
cd /Users/raibach/Documents/development/grace-editor
touch .env
```

Add the following content (adjust credentials as needed):

```bash
# Local PostgreSQL Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/grace_db

# Or if you created a custom user:
# DATABASE_URL=postgresql://grace_user:your_password@localhost:5432/grace_db

# Optional: For Railway production (leave empty for local dev)
# DATABASE_PUBLIC_URL=postgresql://user:password@host:port/database
```

**Common Connection Strings:**

- **Default PostgreSQL (no password):**
  ```
  DATABASE_URL=postgresql://your_macos_username@localhost:5432/grace_db
  ```

- **PostgreSQL with password:**
  ```
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/grace_db
  ```

- **Custom user:**
  ```
  DATABASE_URL=postgresql://grace_user:password@localhost:5432/grace_db
  ```

### Step 5: Initialize Database Schema

```bash
# Run the initialization script
python3 scripts/database/init_database.py
```

This will:
- Connect to your database
- Create all tables, indexes, and functions
- Set up Row-Level Security (RLS) policies
- Verify the schema was created

### Step 6: Apply Migrations

```bash
# Apply projects migration
python3 scripts/database/apply_projects_migration.py
```

### Step 7: Verify Setup

Run the diagnostic script:

```bash
python3 scripts/database/check_local_database.py
```

You should see:
- ✅ DATABASE_URL: Set
- ✅ Connection successful
- ✅ All tables created
- ✅ RLS policies enabled

---

## Quick Setup Script

Here's a one-liner to check if everything is ready:

```bash
# Check PostgreSQL
pg_isready -h localhost -p 5432 && echo "✅ PostgreSQL running" || echo "❌ PostgreSQL not running"

# Check Python dependencies
python3 -c "import psycopg2; print('✅ psycopg2 installed')" 2>/dev/null || echo "❌ psycopg2 not installed"

# Check .env file
[ -f .env ] && echo "✅ .env file exists" || echo "❌ .env file missing"

# Check DATABASE_URL
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ DATABASE_URL set' if os.getenv('DATABASE_URL') else '❌ DATABASE_URL not set')"
```

---

## Troubleshooting

### PostgreSQL Connection Refused

**Problem:** `connection refused` error

**Solutions:**
1. Check if PostgreSQL is running:
   ```bash
   brew services list | grep postgresql
   ```

2. Start PostgreSQL:
   ```bash
   brew services start postgresql@15
   ```

3. Check port:
   ```bash
   lsof -i :5432
   ```

### Authentication Failed

**Problem:** `authentication failed` error

**Solutions:**
1. Check PostgreSQL authentication settings:
   ```bash
   # Edit pg_hba.conf (location varies)
   # macOS Homebrew: /opt/homebrew/var/postgresql@15/pg_hba.conf
   # Look for: local all all trust
   ```

2. Try connecting without password:
   ```
   DATABASE_URL=postgresql://your_username@localhost:5432/grace_db
   ```

3. Reset PostgreSQL password:
   ```sql
   ALTER USER postgres WITH PASSWORD 'new_password';
   ```

### Database Does Not Exist

**Problem:** `database "grace_db" does not exist`

**Solution:**
```bash
# Connect to PostgreSQL
psql postgres

# Create database
CREATE DATABASE grace_db;
\q
```

### Module Not Found: psycopg2

**Problem:** `ModuleNotFoundError: No module named 'psycopg2'`

**Solution:**
```bash
pip3 install psycopg2-binary
```

---

## Next Steps

Once your database is set up:

1. **Test the API connection:**
   ```bash
   python3 -c "from backend.conversation_api import ConversationAPI; import os; from dotenv import load_dotenv; load_dotenv(); api = ConversationAPI(os.getenv('DATABASE_URL')); conn = api.get_db(); print('✅ API connection successful')"
   ```

2. **Start the Flask server:**
   ```bash
   python3 grace_api.py
   ```
   Look for: `✅ Database connection test successful!`

3. **Start the FastAPI server:**
   ```bash
   cd backend
   python3 -m uvicorn main:app --reload
   ```

---

## Connection String Reference

### Local Development
```
postgresql://username:password@localhost:5432/database_name
```

### Railway Internal (Production)
```
postgresql://user:password@postgres.railway.internal:5432/railway
```

### Railway Public (Production)
```
postgresql://user:password@host.proxy.rlwy.net:port/railway
```

---

**Last Updated:** 2024

