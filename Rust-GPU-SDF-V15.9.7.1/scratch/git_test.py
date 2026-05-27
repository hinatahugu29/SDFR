import subprocess
import os
import time

repo_dir = r"e:\blender_addon\外部テスト"
lock_file = os.path.join(repo_dir, ".git", "index.lock")
res_file = os.path.join(repo_dir, "Rust-GPU-SDF-V15.9.7.1", "scratch", "git_res.txt")

with open(res_file, 'w', encoding='utf-8') as out:
    try:
        subprocess.run(["taskkill", "/f", "/im", "git.exe"], capture_output=True)
        out.write("Killed git.\n")
    except Exception as e:
        out.write(f"Taskkill error: {e}\n")

    time.sleep(0.5)

    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            out.write("Removed lock.\n")
        except Exception as e:
            out.write(f"Remove lock error: {e}\n")

    out.write("Running git rm --cached -r ...\n")
    res_rm = subprocess.run(["git", "rm", "--cached", "-r", "."], cwd=repo_dir, capture_output=True)
    out.write(f"RM Return code: {res_rm.returncode}\n")
    out.write(f"RM STDOUT: {res_rm.stdout.decode('utf-8', errors='ignore')[:500]}\n")
    out.write(f"RM STDERR: {res_rm.stderr.decode('utf-8', errors='ignore')[:500]}\n")

    out.write("Staging files...\n")
    res_add = subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
    out.write(f"ADD Return code: {res_add.returncode}\n")
    out.write(f"ADD STDOUT: {res_add.stdout.decode('utf-8', errors='ignore')[:500]}\n")
    out.write(f"ADD STDERR: {res_add.stderr.decode('utf-8', errors='ignore')[:2000]}\n") # Print more STDERR to see the exact error!

    if res_add.returncode == 0:
        out.write("Committing...\n")
        res_commit = subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, capture_output=True)
        out.write(f"COMMIT Return code: {res_commit.returncode}\n")
        out.write(f"COMMIT STDOUT: {res_commit.stdout.decode('utf-8', errors='ignore')}\n")
        out.write(f"COMMIT STDERR: {res_commit.stderr.decode('utf-8', errors='ignore')}\n")
