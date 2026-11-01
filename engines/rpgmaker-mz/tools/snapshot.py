# -*- coding: utf-8 -*-
"""Snapshot pristine originals into <GAME>/_localization/backup/.

usage:  RM_GAME=<game root> python snapshot.py [--apply]
"""
import os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loc_core import GAME, BASE, DATA

DEST = os.path.join(BASE, 'backup')

def copy(src, dst, is_dir=False):
    if not os.path.exists(src):
        print('missing:', src); return 0
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    if is_dir:
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    return 1

def main(apply=False, with_img=False):
    jobs = [
        (os.path.join(GAME, 'data'), os.path.join(DEST, 'data_orig'), True),
        (os.path.join(GAME, 'js', 'plugins.js'), os.path.join(DEST, 'js', 'plugins.js'), False),
        (os.path.join(GAME, 'js', 'plugins'), os.path.join(DEST, 'js', 'plugins'), True),
        (os.path.join(GAME, 'index.html'), os.path.join(DEST, 'index.html'), False),
        (os.path.join(GAME, 'package.json'), os.path.join(DEST, 'package.json'), False),
        (os.path.join(GAME, 'save'), os.path.join(DEST, 'save_orig'), True),
        (os.path.join(GAME, 'fonts'), os.path.join(DEST, 'fonts_orig'), True),
    ]
    if with_img:
        jobs.append((os.path.join(GAME, 'img'), os.path.join(DEST, 'img_orig'), True))
    for src, dst, is_dir in jobs:
        n = copy(src, dst, is_dir)
        print(('  ok ' if n else '  -- '), src.replace(GAME, '.'), '->', dst.replace(GAME, '.'))
    print('snapshot done. img/ is NOT copied by default (966MB); img_redraw.py backs up\n'
          'each file it overwrites. use --with-img for a full copy.')

if __name__ == '__main__':
    main('--apply' in sys.argv, '--with-img' in sys.argv)
