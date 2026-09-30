"""Lossless, verified storage of the unchanged normative decision document.

DECISIONS.json is an ordered index; each named shard is independently a
normative-schema document. load_register reconstructs the exact logical
document and verifies every byte count, hash, count and decision identity.
Historical single-file registers remain readable.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json,re

STORAGE_VERSION='openlogic-translation-decision-storage/1.0.0'
TARGET_BYTES=32*1024*1024
HARD_FILE_BYTES=100*1024*1024

def encoded(value:dict)->bytes:
    return (json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf8')

def document_digest(value:dict)->str:
    return sha256(encoded(value)).hexdigest()

def write_register(document:dict,directory:Path)->list[Path]:
    directory.mkdir(parents=True,exist_ok=True)
    header={k:v for k,v in document.items() if k!='decisions'}
    groups=[];current=[];size=len(encoded({**header,'decisions':[]}))
    for decision in document['decisions']:
        cost=len(encoded(decision))
        if cost+len(encoded({**header,'decisions':[]}))>=HARD_FILE_BYTES:
            raise ValueError('One normative decision exceeds the publication limit; do not omit its occurrences.')
        if current and size+cost>TARGET_BYTES:
            groups.append(current);current=[];size=len(encoded({**header,'decisions':[]}))
        current.append(decision);size+=cost
    if current:groups.append(current)
    shards=[];paths=[]
    for i,group in enumerate(groups,1):
        name=f'DECISIONS-{i:03d}.json';path=directory/name;raw=encoded({**header,'decisions':group})
        if len(raw)>=HARD_FILE_BYTES:raise ValueError('Register shard exceeds publication limit.')
        path.write_bytes(raw);paths.append(path)
        shards.append({'path':name,'bytes':len(raw),'sha256':sha256(raw).hexdigest(),
                       'decisions':len(group),'occurrences':sum(len(x['occurrences']) for x in group),
                       'first_decision_id':group[0]['decision_id'],'last_decision_id':group[-1]['decision_id']})
    index={'storage_schema_version':STORAGE_VERSION,'normative_schema':'translation-decision.schema.json',
           'document_header':header,'logical_document_sha256':document_digest(document),
           'decisions':len(document['decisions']),
           'occurrences':sum(len(x['occurrences']) for x in document['decisions']),
           'shards':shards,'reconstruction':'هره برخه په ثبت شوي ترتيب، د بايټونو او SHA-256 له تصديق وروسته ولولئ۔ د هرې برخې لومړني معلومات بايد له document_header سره عين وي؛ بيا يې پرېکړې په هماغه ترتيب يوځای کړئ۔ هېڅ سرچينه، ژباړه، انتخاب يا پېښه نۀ ده غورځول شوې۔'}
    path=directory/'DECISIONS.json';path.write_bytes(encoded(index));paths.insert(0,path)
    if load_register(path)!=document:raise ValueError('Sharded register reconstruction changed the normative document.')
    return paths

def register_files(path:Path)->list[Path]:
    value=json.loads(path.read_text('utf-8-sig'))
    if 'storage_schema_version' not in value:return [path]
    if value['storage_schema_version']!=STORAGE_VERSION:raise ValueError('Unknown register storage version.')
    names=[x['path'] for x in value['shards']]
    if names!=[f'DECISIONS-{i:03d}.json' for i in range(1,len(names)+1)]:
        raise ValueError('Register shard names/order are not canonical.')
    return [path]+[path.parent/name for name in names]

def load_register(path:Path)->dict:
    value=json.loads(path.read_text('utf-8-sig'))
    if 'storage_schema_version' not in value:return value
    paths=register_files(path);records=[];header=value['document_header']
    if 'decisions' in header:raise ValueError('Index header must not contain decision data.')
    for item,file in zip(value['shards'],paths[1:]):
        raw=file.read_bytes()
        if len(raw)!=item['bytes'] or sha256(raw).hexdigest()!=item['sha256']:
            raise ValueError('Register shard byte/hash mismatch: '+item['path'])
        shard=json.loads(raw)
        if {k:v for k,v in shard.items() if k!='decisions'}!=header:
            raise ValueError('Register shard header mismatch.')
        group=shard['decisions']
        if not group or len(group)!=item['decisions'] or sum(len(x['occurrences']) for x in group)!=item['occurrences']:
            raise ValueError('Register shard counts mismatch.')
        if group[0]['decision_id']!=item['first_decision_id'] or group[-1]['decision_id']!=item['last_decision_id']:
            raise ValueError('Register shard endpoint identity mismatch.')
        records.extend(group)
    if len(records)!=value['decisions'] or sum(len(x['occurrences']) for x in records)!=value['occurrences']:
        raise ValueError('Register total counts mismatch.')
    if len({x['decision_id'] for x in records})!=len(records):raise ValueError('Duplicate decision identity in register.')
    document={**header,'decisions':records}
    if document_digest(document)!=value['logical_document_sha256']:
        raise ValueError('Register logical document hash mismatch.')
    return document

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description='Verify and optionally reconstruct a complete normative decision document.')
    p.add_argument('index',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    d=load_register(a.index)
    if a.output:a.output.write_bytes(encoded(d))
    print(json.dumps({'status':'PASS','decisions':len(d['decisions']),
                      'occurrences':sum(len(x['occurrences']) for x in d['decisions']),
                      'logical_document_sha256':document_digest(d)}))
