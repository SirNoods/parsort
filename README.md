# Parsort

> A human friendly CLI file sorter built around the PARA method by Tiago Forte

Parsort treats a folder (like ~/Downloads) as an inbox and helps you sort files into a structured PARA system:

- Projects
- Areas
- Resources
- Archive

It supports both fully automatic rule based sorting and a guided interactive mode, with transparent logging and safe undo.

If you are not familiar with the PARA method, give this a watch:
https://www.youtube.com/watch?v=T6Mfl1OywM8&pp=ygULUEFSQSBtZXRob2TSBwkJhwoBhyohjO8%3D

## Why Parsort?
My Downloads folder turns into chaos real quick, and I bet others do to.

Parsort helps you:
- preserve intentional structure
- stay in control of where files go
- keep a transparent move log
- undo mistakes safely

It's fast and designed for terminal users who care about structure.

## Installation
### From source (development)
```
git clone https://github.com/SirNoods/parsort.git
cd parsort
pip install -e .
```

### Planned
- AUR package
- PyPI package

## Configuration
Initialize a config:
```
parsort init
```
Or guided setup:
```
parsort init --guided
```
By default, config lives in:
```
~/.config/parsort/config.yml
```

### Example config
```
para_root: "/home/user"

buckets:
  projects: 1_Projects
  areas: 2_Areas
  resources: 3_Resources
  archive: 4_Archive

rules:
  - name: Images
    ext: [png, jpg, jpeg, gif, webp]
    bucket: resources
    path: Images

  - name: Archives
    ext: [zip, rar, 7z, tar, gz]
    bucket: archive
    path: Archives

```

### How Rules Work

Rules match by file extension:
- Extensions are case-insensitive
- Leading dots are ignored
- Rules are evaluated in order
- First match wins

If a rule references an unknown bucket, it is skipped with a warning.

## Usage
### Automatic Sorting
```
parsort sort ~/Downloads
```
- applies rules
- moves matching files
- logs every move
- leaves unmatched files untouched

### Dry run
```
parsort sort ~/Downloads
```
Shows what would happen without moving anything.
Always use this first if you're unsure or testing.

### Guided Mode
```
parsort sort ~/Downloads --guided
```
in guided mode:
- every file is shown to you
- rules are suggestions only
- you choose the bucket
- you browse into the exact subfolder
- you can skip or quit anytime

This is perfect for first time cleanup, large messy inboxes or when you want full control.

### Undo last run
```
parsort undo ~/Downloads --dry-run
```

## Roadmap
Planned features:
- optional image preview via chafa
- better rule matching, and more configurable rule options
- batch confirmation
- AUR packaging

## Contributing
Issues and PRs welcome!

MIT License :) 