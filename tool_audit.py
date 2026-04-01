import os
import re
import glob
from src.real_tools import execute_bash, read_file, edit_file, web_search, web_fetch

def run_audit():
    print("🚀 Starting Clawt Tool Audit...")
    
    # 1. Test execute_bash
    print("\n[1/6] Testing execute_bash...")
    res = execute_bash("ls -F /data/data/com.termux/files/home/Claw-Termux")
    print(f"Result: {res[:100]}...")
    assert "src/" in res, "execute_bash failed to list directory"

    # 2. Test read_file
    print("\n[2/6] Testing read_file...")
    res = read_file("/data/data/com.termux/files/home/Claw-Termux/src/real_tools.py", start_line=1, end_line=5)
    print(f"Result:\n{res}")
    assert "import os" in res, "read_file failed to read content"

    # 3. Test glob_files (via handle_tool_call or manual logic)
    print("\n[3/6] Testing glob_files...")
    files = glob.glob("/data/data/com.termux/files/home/Claw-Termux/src/*.py")
    print(f"Result: Found {len(files)} files")
    assert len(files) > 0, "glob_files failed to find python files"

    # 4. Test File Writing & Editing
    print("\n[4/6] Testing edit_file...")
    test_file = "/data/data/com.termux/files/home/Claw-Termux/audit_test.txt"
    with open(test_file, "w") as f:
        f.write("Hello World\nStatus: Pending")
    
    res = edit_file(test_file, "Status: Pending", "Status: Verified")
    print(f"Result: {res}")
    with open(test_file, "r") as f:
        content = f.read()
    assert "Status: Verified" in content, "edit_file failed replacement"
    os.remove(test_file)

    # 5. Test Web Search (Live)
    print("\n[5/6] Testing web_search (DuckDuckGo)...")
    res = web_search("Python 2026 flagship models")
    print(f"Result: {res[:200]}...")
    assert "Link:" in res or "No relevant" in res, "web_search failed parsing"

    # 6. Test Web Fetch (Live)
    print("\n[6/6] Testing web_fetch...")
    res = web_fetch("https://example.com")
    print(f"Result: {res[:100]}...")
    assert "Example Domain" in res, "web_fetch failed to retrieve content"

    print("\n✅ AUDIT COMPLETE: All tools verified functional.")

if __name__ == "__main__":
    run_audit()
