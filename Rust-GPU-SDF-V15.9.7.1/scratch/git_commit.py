import os
import subprocess
import time

repo_dir = r"e:\blender_addon\外部テスト"
lock_file = os.path.join(repo_dir, ".git", "index.lock")
res_file = os.path.join(repo_dir, "Rust-GPU-SDF-V15.9.7.1", "scratch", "git_res.txt")

with open(res_file, 'w', encoding='utf-8') as out:
    # Kill any running git processes
    try:
        subprocess.run(["taskkill", "/f", "/im", "git.exe"], capture_output=True)
        out.write("Killed git processes.\n")
    except Exception as e:
        out.write(f"Error killing git: {e}\n")

    # Wait a brief moment
    time.sleep(0.5)

    # Remove the lock file if it exists
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            out.write("Removed index.lock.\n")
        except Exception as e:
            out.write(f"Error removing lock: {e}\n")

    # Run git add and commit immediately
    try:
        out.write("Running git add . ...\n")
        add_res = subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        stdout = add_res.stdout.decode('utf-8', errors='ignore')
        stderr = add_res.stderr.decode('utf-8', errors='ignore')
        out.write(f"Add Exit code: {add_res.returncode}\n")
        out.write(f"Add STDOUT (first 500): {stdout[:500]}\n")
        out.write(f"Add STDERR (first 500): {stderr[:500]}\n")
        
        if add_res.returncode == 0:
            out.write("Running git commit ...\n")
            commit_res = subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, capture_output=True)
            commit_stdout = commit_res.stdout.decode('utf-8', errors='ignore')
            commit_stderr = commit_res.stderr.decode('utf-8', errors='ignore')
            out.write(f"Commit Exit code: {commit_res.returncode}\n")
            out.write(f"Commit STDOUT: {commit_stdout}\n")
            out.write(f"Commit STDERR: {commit_stderr}\n")
    except Exception as e:
        out.write(f"Error running git commands: {e}\n")

print("Output written to:", res_file)
