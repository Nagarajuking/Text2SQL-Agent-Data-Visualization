"""
Quick setup script to help users get started.

This script:
1. Checks if .env file exists
2. Prompts for Google API key if needed
3. Validates the database exists
4. Provides next steps
"""

import os
from pathlib import Path


def main():
    """Run setup checks and guide user."""
    print("Text-to-SQL System - Setup Check\n")
    
    # Check 1: .env file
    env_path = Path(".env")
    if not env_path.exists():
        print("[ERROR] .env file not found")
        print("   Creating .env from template...\n")
        
        # Copy from example
        example_path = Path(".env.example")
        if example_path.exists():
            with open(example_path) as f:
                content = f.read()
            
            # Prompt for API key
            print("Please enter your Google Gemini API key")
            print("   (Get one from: https://makersuite.google.com/app/apikey)")
            api_key = input("   API Key: ").strip()
            
            # Replace placeholder
            content = content.replace("GOOGLE_API_KEY=your_api_key_here", f"GOOGLE_API_KEY={api_key}")
            
            # Write .env
            with open(".env", "w") as f:
                f.write(content)
            
            print("   [SUCCESS] .env file created!\n")
        else:
            print("   [WARNING] .env.example not found. Please create .env manually.\n")
    else:
        print("[SUCCESS] .env file exists\n")
    
    # Check 2: Database
    db_path = Path("chinook.db")
    if db_path.exists():
        print("[SUCCESS] chinook.db database found\n")
    else:
        print("[ERROR] chinook.db not found")
        print("   Please ensure the database file is in the project directory.\n")
    
    # Check 3: Dependencies
    print("Installing dependencies...")
    os.system("pip install -r requirements.txt")
    print()
    
    # Final instructions
    print("=" * 60)
    print("Setup Complete! Next steps:")
    print("=" * 60)
    print()
    print("1. Verify your .env file has a valid GOOGLE_API_KEY")
    print("2. Run the application:")
    print("   streamlit run main.py")
    print()
    print("3. Open your browser to: http://localhost:8501")
    print()
    print("Happy querying!")
    print()


if __name__ == "__main__":
    main()
