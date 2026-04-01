import sys
import os
from src.real_tools import google_search

def test():
    print("🚀 Testing Elite Google Search...")
    query = "Python 3.12 new features official documentation"
    results = google_search(query)
    
    if "Error" in results:
        print(f"❌ {results}")
        sys.exit(1)
        
    print("\n✅ Search Successful! Results preview:")
    # Print first 500 chars of result
    print("-" * 40)
    print(results[:1000] + "...")
    print("-" * 40)
    
    if "Snippet:" in results and "Link:" in results:
        print("\n✨ Verified: Snippets and Links are present.")
    else:
        print("\n⚠️  Warning: Snippets or Links might be missing.")

if __name__ == "__main__":
    test()
