#!/usr/bin/env python3
"""Record a macOS WPS window while an agent emits CodeBuddy stream JSON."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def screen_index(screen):
    p = subprocess.run(['ffmpeg', '-hide_banner', '-f', 'avfoundation', '-list_devices', 'true', '-i', ''], capture_output=True, text=True)
    video = p.stderr.split('AVFoundation audio devices:')[0]
    m = re.search(r'\[(\d+)\]\s+Capture screen\s+' + re.escape(str(screen)) + r'\b', video)
    if not m:
        raise RuntimeError('Cannot find the requested AVFoundation screen. Check FFmpeg and Screen Recording permission.')
    return int(m.group(1))


def capture(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    log = (args.agent_log or output / 'trajectory.jsonl').resolve()
    if log.exists():
        raise RuntimeError('Agent log already exists: ' + str(log))
    log.parent.mkdir(parents=True, exist_ok=True)
    events = args.events.resolve() if args.events else output / 'wps-events.jsonl'
    if events.exists():
        raise RuntimeError('WPS event log already exists: ' + str(events))
    index = screen_index(args.screen)
    x, y, width, height = args.crop
    if min(x, y) < 0 or min(width, height) <= 0 or any(n % 2 for n in (x, y, width, height)):
        raise RuntimeError('Crop values must be nonnegative even pixel coordinates and positive even dimensions.')
    progress = output / 'capture-progress.txt'
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y', '-f', 'avfoundation', '-framerate', '15', '-capture_cursor', '1', '-i', f'{index}:none', '-vf', f'crop={width}:{height}:{x}:{y},fps=15', '-c:v', 'libx264', '-threads', '2', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', '-stats_period', '0.2', '-progress', str(progress), str(output / 'wps.mp4')]
    process = None
    status = None
    start = None
    with (output / 'capture.log').open('w') as capture_log:
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=capture_log, stderr=subprocess.STDOUT)
            deadline = time.time() + 20
            while time.time() < deadline:
                if process.poll() is not None:
                    raise RuntimeError('Screen capture stopped. Check capture.log.')
                if progress.exists():
                    entries = dict(line.split('=', 1) for line in progress.read_text().splitlines() if '=' in line)
                    if int(entries.get('frame', '0')) > 0:
                        start = time.time() - int(entries.get('out_time_us', '0')) / 1_000_000
                        break
                time.sleep(.1)
            if start is None:
                raise RuntimeError('No screen frames arrived. Check capture.log and screen permissions.')
            metadata = {'start_epoch': start, 'crop': args.crop, 'screen': args.screen, 'audio': False, 'sync': 'first FFmpeg progress timestamp minus encoded output time; approximate'}
            (output / 'capture.json').write_text(json.dumps(metadata, indent=2) + '\n')
            env = os.environ.copy()
            env['WPS_DEMO_EVENTS'] = str(events)
            with log.open('w') as agent_output, (log.parent / (log.name + '.stderr')).open('w') as error:
                status = subprocess.run(args.command, cwd=args.cwd, env=env, stdout=agent_output, stderr=error).returncode
            time.sleep(2)
        finally:
            if process and process.poll() is None:
                try:
                    process.stdin.write(b'q\n')
                    process.stdin.flush()
                    process.wait(timeout=20)
                except (BrokenPipeError, subprocess.TimeoutExpired):
                    process.terminate()
                    process.wait()
    if log != output / 'trajectory.jsonl':
        (output / 'trajectory.jsonl').write_bytes(log.read_bytes())
    if events.exists() and events != output / 'wps-events.jsonl':
        (output / 'wps-events.jsonl').write_bytes(events.read_bytes())
    (output / 'agent-exit.txt').write_text(str(status) + '\n')
    if process.returncode != 0:
        raise RuntimeError('Screen capture failed; inspect capture.log.')
    subprocess.run([sys.executable, str(Path(__file__).with_name('render.py')), str(output)], check=True)
    if status:
        print(f'Agent exited {status}; recording preserved at {output}', file=sys.stderr)
        return status
    print(f'Recording and event timeline saved at {output}')
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True, help='New output directory')
    p.add_argument('--crop', type=int, nargs=4, required=True, metavar=('X', 'Y', 'WIDTH', 'HEIGHT'), help='Even pixel crop on the capture screen')
    p.add_argument('--screen', type=int, default=0, help='AVFoundation screen number (default 0)')
    p.add_argument('--cwd', type=Path, required=True, help='Agent working directory')
    p.add_argument('--agent-log', type=Path, help='Fresh JSONL path writable by the agent sandbox; copied into output afterward')
    p.add_argument('--events', type=Path, help='Fresh writer-event path if the writer cannot use WPS_DEMO_EVENTS; copied afterward')
    p.add_argument('command', nargs=argparse.REMAINDER, help='Command emitting CodeBuddy stream JSON after --')
    args = p.parse_args()
    if args.command and args.command[0] == '--':
        args.command = args.command[1:]
    if not args.command:
        p.error('supply the agent command after --')
    return capture(args)


if __name__ == '__main__':
    sys.exit(main())
