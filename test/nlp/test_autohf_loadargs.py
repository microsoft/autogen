def test_load_args():
    import subprocess
    import sys

    subprocess.call([sys.executable, "load_args.py", "--output_dir", "data/"], shell=True)
