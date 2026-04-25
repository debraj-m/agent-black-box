import argparse, json, subprocess, time
from pathlib import Path

def git_output(*args):
    try:
        return subprocess.check_output(['git', *args], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return ''

def record(command, root='.'):
    root = Path(root).resolve()
    run_id = time.strftime('%Y%m%d-%H%M%S')
    outdir = root / '.agent-black-box' / 'runs' / run_id
    outdir.mkdir(parents=True, exist_ok=True)
    before = git_output('status','--short')
    start = time.time()
    proc = subprocess.run(command, cwd=root, text=True, capture_output=True)
    end = time.time()
    after = git_output('status','--short')
    diff = git_output('diff')
    (outdir/'stdout.txt').write_text(proc.stdout, encoding='utf-8')
    (outdir/'stderr.txt').write_text(proc.stderr, encoding='utf-8')
    (outdir/'diff.patch').write_text(diff, encoding='utf-8')
    manifest = {'command': command, 'exit_code': proc.returncode, 'duration_seconds': round(end-start, 3), 'status_before': before.splitlines(), 'status_after': after.splitlines()}
    (outdir/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest, outdir

def main():
    parser = argparse.ArgumentParser(description='Record what a command did to your repo.')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        raise SystemExit('Pass a command after --')
    manifest, outdir = record(command)
    print(f'recorded: {outdir}')
    print(json.dumps(manifest, indent=2))
    raise SystemExit(manifest['exit_code'])

if __name__ == '__main__':
    main()
