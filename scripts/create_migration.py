#!/usr/bin/env python3
"""
Create a new database migration.
"""
import sys
import subprocess
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def create_migration():
    """Create a new Alembic migration."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/create_migration.py <migration_message>")
        sys.exit(1)
    
    message = " ".join(sys.argv[1:])
    
    # Create migration
    result = subprocess.run(
        ["alembic", "revision", "--autogenerate", "-m", message],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("Migration created successfully")
        print(result.stdout)
    else:
        print(f"Migration creation failed: {result.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    create_migration()


