# Localfile Sychronizer Tool

This is a tool I wrote for my partner who wanted to backup 4TB of photos across multiple external drives, I could not find a nice free tool on windows to do this so decided to write it myself.

### Project Goals

Dry Run - allow the user to preview all possible changes without writeing any data to the drives
Sync Modified - allow the applications to sync files based on modification date
Sync Deleted - allow syncing deletions

Provide protection against dumb mistakes (I am prone to dumb mistakes, so I guess others are)

### Setup

make a virtual environment (you really should)

pip install requirements.txt
