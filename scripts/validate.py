"""Validate every collection, IDs, environment references and public content."""
import json
import re
import zipfile
from pathlib import Path

import jsonschema
import yaml

ROOT=Path(__file__).resolve().parents[1]

def validate():
    schema=json.loads((ROOT/'schemas/insomnia.schema.5.1.json').read_text(encoding='utf-8'))
    validator=jsonschema.Draft202012Validator(schema)
    ids=set();total=0;files=list((ROOT/'collections').rglob('*.yaml'));scripts={};fixtures={}
    lite_summary=json.loads((ROOT/'catalog/lite-summary.json').read_text())
    summary=json.loads((ROOT/'catalog/summary.json').read_text())
    sources=[(p.relative_to(ROOT).as_posix(),p.read_text(encoding='utf-8')) for p in files]
    with zipfile.ZipFile(ROOT/lite_summary['optional_archive']) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist())=={item['file'] for item in summary['files']}
        sources.extend((name,archive.read(name).decode('utf-8')) for name in archive.namelist())
    forbidden=re.compile(r'api\d+(?:sales|preview)?\.successfactors\.com|cust_|https?://[^\s\"\']*ondemand\.com',re.I)
    global_doc=yaml.safe_load((ROOT/'environments/SuccessFactors.yaml').read_text(encoding='utf-8'))
    validator.validate(global_doc)
    global_env=global_doc['environments']['data']
    def visit(nodes,env):
        nonlocal total
        for n in nodes:
            id_=n['meta']['id']
            assert id_ not in ids, 'Duplicate ID: '+id_
            ids.add(id_)
            if 'method' in n:
                total+=1
                for kind,code in n.get('scripts',{}).items(): scripts[code]=kind
                if n['name'].startswith('Conectar —'): fixtures['connect']=n['scripts']['afterResponse']
                if n['name']=='01 — Token BTP': fixtures['btp']=n['scripts']['afterResponse']
                if n['name']=='02 — Token SuccessFactors via Destination': fixtures['destination']=n['scripts']['afterResponse']
                if n['name']=='Alternativa — Token direto SAML': fixtures['saml']=n['scripts']['afterResponse']
                code=n.get('scripts',{}).get('afterResponse','')
                if "'key_FOCompany'" in code: fixtures['company_key']=code
                if "'key_User'" in code: fixtures['user_key']=code
                for var in re.findall(r'\{\{\s*_\.([A-Za-z0-9_]+)\s*\}\}',json.dumps(n)):
                    assert var in env, 'Undefined environment variable: '+var
                if n['method'] in ('POST','MERGE','DELETE') and '/oauth/token' not in n['url'] and 'btp_token_url' not in n['url']:
                    assert n['meta']['description'], 'Missing operation description'
            else: visit(n.get('children',[]),env)
    for name,text in sources:
        p=Path(name)
        assert not any(isinstance(token,(yaml.tokens.AnchorToken,yaml.tokens.AliasToken)) for token in yaml.scan(text)), 'YAML aliases are incompatible with strict Insomnia import limits: '+str(p)
        assert not forbidden.search(text), 'Instance-specific content: '+name
        doc=yaml.safe_load(text)
        validator.validate(doc)
        for obj in [doc['meta'],doc['environments']['meta']]:
            assert obj['id'] not in ids
            ids.add(obj['id'])
        env=dict(global_env,**doc['environments']['data'])
        for key,value in env.items():
            if any(s in key for s in ('token','secret','saml_assertion','sf_company_id','sf_client_id','btp_client_id','destination_service_url')):
                assert value=='', 'Credential/configuration must be blank: '+key
        visit(doc['collection'],env)
    assert total==summary['requests']+lite_summary['requests']
    assert len(files)==lite_summary['collections']==1
    assert len(sources)==summary['collections']+1
    for p in (ROOT/'catalog').glob('*'):
        if p.is_file(): assert not forbidden.search(p.read_text(encoding='utf-8')), 'Instance-specific catalog: '+p.name
    (ROOT/'.local').mkdir(exist_ok=True)
    (ROOT/'.local/script-fixtures.json').write_text(json.dumps(dict(scripts=list(scripts),fixtures=fixtures)),encoding='utf-8')
    print(f'OK: {lite_summary["requests"]} active requests in one collection; {summary["requests"]} optional requests in ZIP; official schema, unique IDs, variable references, generic content and blank credentials.')

if __name__=='__main__': validate()
