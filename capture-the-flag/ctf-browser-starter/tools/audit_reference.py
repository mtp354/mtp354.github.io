#!/usr/bin/env python3
"""Create a static evidence index; never execute the extracted JASS."""
from __future__ import annotations
import argparse
import json
import re
import struct
from pathlib import Path

class Reader:
    def __init__(self, data: bytes):
        self.data, self.pos = data, 0
    def take(self, n: int) -> bytes:
        if self.pos+n > len(self.data):
            raise ValueError('Truncated object data')
        result = self.data[self.pos:self.pos+n]; self.pos += n
        return result
    def int(self) -> int: return struct.unpack('<i', self.take(4))[0]
    def real(self) -> float: return struct.unpack('<f', self.take(4))[0]
    def id(self) -> str: return self.take(4).decode('latin1')
    def string(self) -> str:
        end = self.data.find(b'\0',self.pos)
        if end < 0: raise ValueError('Unterminated string')
        return self.take(end-self.pos+1)[:-1].decode('utf-8',errors='replace')

def read_objects(path: Path, extended: bool = False) -> dict:
    r=Reader(path.read_bytes()); version=r.int()
    if version not in (1,2): raise ValueError(f'Unsupported object format {version}')
    result={'version':version, 'tables':{}}
    for table in ('original','custom'):
        rows=[]
        count=r.int()
        if not 0 <= count <= 100000: raise ValueError('Invalid object count')
        for _ in range(count):
            original,new,n=r.id(),r.id(),r.int(); fields=[]
            if not 0 <= n <= 100000: raise ValueError('Invalid field count')
            for _ in range(n):
                field,kind=r.id(),r.int()
                level,column=(r.int(),r.int()) if extended else (None,None)
                if kind==0: value=r.int()
                elif kind in (1,2): value=r.real()
                elif kind==3: value=r.string()
                else: raise ValueError(f'Unknown field type {kind}')
                terminator=r.id()
                fields.append({'field':field, 'kind':kind, 'level':level,'column':column,'value':value})
            rows.append({'base':original,'id':new if new!='\0'*4 else original,'fields':fields})
        result['tables'][table]=rows
    if r.pos != len(r.data): raise ValueError(f'Trailing bytes: {len(r.data)-r.pos}')
    return result

def audit(folder: Path) -> dict:
    script=(folder/'war3map.j').read_bytes().decode('utf-8',errors='replace')
    funcs=[]
    for m in re.finditer(r'^function (\w+) .*?^endfunction', script, re.M|re.S):
        funcs.append({'name':m.group(1),'start_line':script.count('\n',0,m.start())+1,
                      'end_line':script.count('\n',0,m.end())+1})
    regions=[]
    for m in re.finditer(r'^\s*set gg_rct_(\w+) = Rect\( ([^\n]+) \)',script,re.M):
        regions.append({'name':m.group(1),'bounds':[float(x) for x in m.group(2).split(',')],
                        'line':script.count('\n',0,m.start())+1})
    output={'line_count':len(script.splitlines()),'function_count':len(funcs),
            'init_trigger_count':sum(x['name'].startswith('InitTrig_') for x in funcs),
            'functions':funcs,'regions':regions}
    (folder/'jass-index.json').write_text(json.dumps(output,indent=2)+'\n')
    (folder/'regions.json').write_text(json.dumps(regions,indent=2)+'\n')
    for name,extended in [('war3map.w3u',False),('war3map.w3t',False),('war3map.w3a',True)]:
        path=folder/name
        if path.exists():
            (folder/(name+'.json')).write_text(json.dumps(read_objects(path,extended),indent=2)+'\n')
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path)
    result=audit(p.parse_args().folder)
    print(json.dumps({k:result[k] for k in ['line_count','function_count','init_trigger_count']},indent=2))
