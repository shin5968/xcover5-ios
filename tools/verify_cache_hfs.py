#!/usr/bin/env python3
"""Independently parse HFS with 7-Zip and hash extracted streams (no extra 3GiB copy).
Usage on Linux/WSL: 7ZZ IMAGE
"""
import hashlib,json,subprocess,sys
from pathlib import Path
seven,image=sys.argv[1:3]
items=json.loads(Path(__file__).with_name('cache-layout.json').read_text())
for item in items:
 p=subprocess.Popen([seven,'e','-so',image,'XCIOSCACHE/'+item['file']],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 h=hashlib.sha256();n=0
 while data:=p.stdout.read(1024*1024):h.update(data);n+=len(data)
 errors=p.stderr.read();rc=p.wait()
 assert rc==0 and n==item['size'] and h.hexdigest()==item['sha256'],(item['file'],rc,n,errors)
 print(item['file'],n,'SHA256 PASS',flush=True)
p=subprocess.run([seven,'e','-so',image,'XCIOSCACHE/m28-cache-proof.txt'],capture_output=True,check=True)
assert p.stdout==b'XCOVER5 M28 userdata cache volume verified\n'
print('Independent HFS extraction: 43 complete files and volume proof PASS')
