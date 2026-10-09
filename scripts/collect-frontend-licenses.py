"""Collect installed npm package notices for the distributable desktop folder."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def packages(directory):
    if not directory.is_dir():
        return
    for candidate in sorted(directory.iterdir()):
        if candidate.name.startswith('.') or not candidate.is_dir():
            continue
        candidates = sorted(candidate.iterdir()) if candidate.name.startswith('@') else [candidate]
        for package in candidates:
            if (package / 'package.json').is_file():
                yield package
                yield from packages(package / 'node_modules')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    sections = ['GuGuGaGa frontend: original notices from installed npm packages.\n'
                'Build tools and development-only packages may also be listed.\n']
    seen = set()
    for package in packages(ROOT / 'node_modules'):
        metadata = json.loads((package / 'package.json').read_text(encoding='utf-8'))
        key = (metadata.get('name', package.name), metadata.get('version', 'unknown'))
        if key in seen:
            continue
        seen.add(key)
        license_name = metadata.get('license', metadata.get('licenses', 'See package source'))
        sections.append('\n' + '=' * 78 + '\n' + f'{key[0]} {key[1]}\nDeclared license: {license_name}\n')
        repository = metadata.get('repository', '')
        if isinstance(repository, dict):
            repository = repository.get('url', '')
        if repository:
            sections.append(f'Source: {repository}\n')
        for source in sorted(package.iterdir()):
            if source.is_file() and source.name.upper().startswith(('LICENSE', 'LICENCE', 'COPYING', 'NOTICE')):
                sections.append('\n' + source.name + '\n' + source.read_text(encoding='utf-8', errors='replace') + '\n')
    if not seen:
        raise SystemExit('No installed npm packages found. Run npm ci before packaging.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(''.join(sections), encoding='utf-8')
    print(f'Collected notices for {len(seen)} installed packages.')


if __name__ == '__main__':
    main()
