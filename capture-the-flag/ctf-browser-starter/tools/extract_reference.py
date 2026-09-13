#!/usr/bin/env python3
"""Read selected data files from a legacy, unencrypted Warcraft III MPQ map.

This is a deliberately narrow read-only extractor, not a general MPQ library.
Supported: MPQ v0/v1 32-bit offsets, unencrypted members, raw/zlib/bzip2 sectors.
Unsupported compression/encryption is reported, never silently guessed.
Does not execute map scripts or extract model, texture, or sound assets.
"""
from __future__ import annotations
import argparse
import bz2
import hashlib
import json
import math
from pathlib import Path
import struct
import zlib

MASK = 0xffffffff

def crypt_table() -> list[int]:
    table = [0] * 1280
    seed = 0x100001
    for low in range(256):
        for bank in range(5):
            seed = (125 * seed + 3) % 0x2aaaab
            upper = (seed & 0xffff) << 16
            seed = (125 * seed + 3) % 0x2aaaab
            table[bank * 256 + low] = upper | (seed & 0xffff)
    return table

TABLE = crypt_table()

def mpq_hash(name: str, bank: int) -> int:
    a, b = 0x7fed7fed, 0xeeeeeeee
    for c in name.upper().encode('ascii'):
        a = (TABLE[bank * 256 + c] ^ ((a + b) & MASK)) & MASK
        b = (c + a + 33 * b + 3) & MASK
    return a

def decode_table(data: bytes, key: int) -> bytes:
    if len(data) % 4:
        raise ValueError('Table has a partial word')
    feedback = 0xeeeeeeee
    out = bytearray()
    for (cipher,) in struct.iter_unpack('<I', data):
        feedback = (feedback + TABLE[1024 + (key & 255)]) & MASK
        clear = (cipher ^ ((key + feedback) & MASK)) & MASK
        out.extend(struct.pack('<I', clear))
        key = (((~key << 21) + 0x11111111) | (key >> 11)) & MASK
        feedback = (clear + 33 * feedback + 3) & MASK
    return bytes(out)

class LegacyMap:
    def __init__(self, blob: bytes):
        offsets = [i for i in range(0, min(len(blob), 2**20), 512)
                   if blob[i:i+4] == b'MPQ\x1a']
        if not offsets:
            raise ValueError('No aligned MPQ header in first MiB')
        self.base = offsets[0]
        self.data = blob[self.base:]
        (magic, hsize, asize, version, shift, hp, bp, hn, bn) = struct.unpack_from('<4sIIHHIIII', self.data)
        if version not in (0, 1) or shift > 16 or hn > 2**20 or bn > 2**20:
            raise ValueError('Unsupported MPQ header')
        self.sector_size = 512 << shift
        self.hashes = list(struct.iter_unpack('<IIHHI', decode_table(self.slice(hp, hn*16), mpq_hash('(hash table)', 3))))
        self.blocks = list(struct.iter_unpack('<IIII', decode_table(self.slice(bp, bn*16), mpq_hash('(block table)', 3))))

    def slice(self, pos: int, length: int) -> bytes:
        if pos < 0 or length < 0 or pos + length > len(self.data):
            raise ValueError('MPQ range out of bounds')
        return self.data[pos:pos+length]

    @staticmethod
    def decompress(data: bytes, expected: int, compressed: bool) -> bytes:
        if len(data) == expected:
            return data
        if not compressed or not data:
            raise ValueError('Unexpected sector length')
        mask, payload = data[0], data[1:]
        if mask == 2:
            result = zlib.decompress(payload)
        elif mask == 16:
            result = bz2.decompress(payload)
        else:
            raise ValueError(f'Unsupported compression mask {mask:#x}')
        if len(result) != expected:
            raise ValueError('Decompressed length mismatch')
        return result

    def read(self, name: str) -> bytes:
        a, b = mpq_hash(name, 1), mpq_hash(name, 2)
        found = next((h for h in self.hashes if h[:2] == (a, b) and h[4] < len(self.blocks)), None)
        if found is None:
            raise KeyError(name)
        pos, packed, size, flags = self.blocks[found[4]]
        if not flags & 0x80000000:
            raise ValueError('Member not present')
        if flags & 0x10000:
            raise ValueError('Encrypted members not supported')
        if flags & 0x100:
            raise ValueError('PKWARE-implode members not supported')
        raw = self.slice(pos, packed)
        if size == 0:
            return b''
        if not flags & 0x200:
            if len(raw) != size:
                raise ValueError('Raw member length mismatch')
            return raw
        if flags & 0x1000000:
            return self.decompress(raw, size, True)
        count = math.ceil(size / self.sector_size)
        pointers = struct.unpack_from(f'<{count+1}I', raw)
        chunks = []
        for i in range(count):
            start, end = pointers[i:i+2]
            if not 0 <= start <= end <= len(raw):
                raise ValueError('Sector range out of bounds')
            chunks.append(self.decompress(raw[start:end], min(self.sector_size, size-i*self.sector_size), True))
        return b''.join(chunks)

NAMES = ['war3map.j', 'war3map.wts', 'war3map.w3i', 'war3map.w3r',
         'war3map.w3u', 'war3map.w3a', 'war3map.w3t', 'war3map.w3q',
         'war3map.w3b', 'war3map.w3d', 'war3map.wtg', 'war3map.wct',
         'war3map.w3e', 'war3map.wpm', 'war3mapUnits.doo', 'war3map.doo',
         'war3map.imp', 'war3mapMisc.txt', 'war3mapSkin.txt']

def extract(source: Path, out: Path) -> dict:
    blob = source.read_bytes()
    archive = LegacyMap(blob)
    out.mkdir(parents=True, exist_ok=True)
    report = {'source_name': source.name, 'source_sha256': hashlib.sha256(blob).hexdigest(),
              'source_bytes': len(blob), 'mpq_offset': archive.base, 'members': [], 'errors': {}}
    for name in NAMES:
        try:
            data = archive.read(name)
        except KeyError:
            continue
        except (ValueError, struct.error, zlib.error, OSError) as exc:
            report['errors'][name] = str(exc)
            continue
        (out / name).write_bytes(data)
        report['members'].append({'name': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    (out / 'extraction-manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--out', type=Path, default=Path('reference-private/wc3/extracted'))
    args = parser.parse_args()
    print(json.dumps(extract(args.map, args.out), indent=2))
