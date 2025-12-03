import os
import subprocess

def commit_and_push_all(commit_message="Update readme instructions"):
    """
    Stages all changes, commits with the provided message,
    and pushes to 'main'. If 'main' doesn't exist, tries 'master'.
    """
    # Make sure we're in the notebook's directory
    notebook_dir = os.path.dirname(os.path.abspath("__file__"))
    os.chdir(notebook_dir)

    # Stage all changes
    subprocess.run(["git", "add", "."])

    # Commit with the provided message
    subprocess.run(["git", "commit", "-m", commit_message])

    # Push to default remote (origin) and branch (main or master)
    try:
        subprocess.run(["git", "push", "origin", "main"], check=True)
    except subprocess.CalledProcessError:
        # If main branch doesn't exist, try master
        subprocess.run(["git", "push", "origin", "master"])
