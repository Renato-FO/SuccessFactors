"""Keep Git Sync small and package the complete library for optional import."""
import copy
import json
import zipfile
from pathlib import Path

import yaml
from generate import auth_folder,dump_yaml,uid,req,param,folder
from setup_collection import attach_setup,SETUP_DEFAULTS

ESSENTIAL = ['User','Photo','EmpJob','FOCompany','FOLocation']

def package(root):
    root=Path(root).resolve()
    summary=json.loads((root/'catalog/summary.json').read_text())
    archive=root/'optional/successfactors-complete.zip'
    archive.parent.mkdir(exist_ok=True)
    source={item['file']:(root/item['file']) for item in summary['files']}
    generated=all(path.exists() for path in source.values())
    if generated:
        docs={name:yaml.safe_load(path.read_text(encoding='utf-8')) for name,path in source.items()}
    else:
        with zipfile.ZipFile(archive) as z:
            docs={name:yaml.safe_load(z.read(name).decode('utf-8')) for name in source}
    identity='collections/SuccessFactors-Essencial.yaml'
    env={'next_page_url':'','user_email':'user@example.com','manager_id':'MANAGER_ID','delegator_id':'DELEGATOR_ID','delegatee_id':'DELEGATEE_ID'}
    by_entity={}
    for name,doc in docs.items():
        if '/Leitura-' not in name: continue
        for entity in doc['collection'][1:]:
            if entity['name'] in ESSENTIAL:
                selected=copy.deepcopy(entity)
                selected['children']=[r for r in selected['children'] if r.get('method')=='GET' and r['name'].startswith(('01 ','02 ','03 ','04 '))]
                by_entity[entity['name']]=selected
                key='key_'+entity['name']
                if key in doc['environments']['data']: env[key]=doc['environments']['data'][key]
    assert all(name in by_entity for name in ESSENTIAL)
    def query(identity,name,entity,values):
        return req('lite-flow/'+identity,name,'/odata/v2/'+entity,params=[param('$format','json'),param('$top','{{ _.page_size }}')]+[param(k,v) for k,v in values.items()])
    by_entity['User']['children'].append(query('user-manager','Usuario ativo e gestor por email','User',{'$filter':"status eq 't' and email eq '{{ _.user_email }}'",'$select':'userId,manager/userId','$expand':'manager'}))
    by_entity['Photo']['children'].append(query('photo-user','Foto do usuario — tipo 1','Photo',{'$filter':"userId eq '{{ _.user_id }}' and photoType eq 1"}))
    by_entity['EmpJob']['children'].extend([
        query('job-user','Cargo e estrutura por usuario','EmpJob',{'$filter':"userId eq '{{ _.user_id }}'",'$select':'userId,managerId,jobTitle,company,location,startDate,seqNumber'}),
        query('job-reports','Subordinados do gestor','EmpJob',{'$filter':"managerId eq '{{ _.manager_id }}' and userId ne '{{ _.user_id }}'",'$select':'userId,managerId,jobTitle,userNav/displayName,userNav/email','$expand':'userNav'})])
    by_entity['FOCompany']['children'].append(query('company-code','Empresa por codigo','FOCompany',{'$filter':"externalCode eq '{{ _.company_code }}'"}))
    by_entity['FOLocation']['children'].append(query('location-code','Local por codigo','FOLocation',{'$filter':"externalCode eq '{{ _.location_code }}'"}))
    delegations=[
        folder('lite/delegate-detail','AutoDelegateDetail',[query('delegate-details','Delegacoes recebidas','AutoDelegateDetail',{'$filter':"delegatee eq '{{ _.delegatee_id }}'",'$select':'AutoDelegateConfig_delegator'})]),
        folder('lite/delegate-config','AutoDelegateConfig',[query('delegate-config','Configuracao do delegador','AutoDelegateConfig',{'$filter':"delegator eq '{{ _.delegator_id }}'",'$select':'delegator,delegationStatus,startTime,endTime,delegatorNav/displayName','$expand':'delegatorNav'})])]
    start=docs['collections/00-Inicio/Diagnostico-e-Consultas.yaml']
    diagnostics=copy.deepcopy(start['collection'][1:4])
    children=[auth_folder(identity)]+diagnostics+[by_entity[name] for name in ESSENTIAL]+delegations
    def remap(items):
        for item in items:
            item['meta']['id']=uid('req' if 'method' in item else 'fld','lite/'+item['meta']['id'])
            remap(item.get('children',[]))
    remap(children)
    lite=dict(type='collection.insomnia.rest/5.0',schema_version='5.1',name='SuccessFactors | Essencial',
        meta=dict(id=uid('wrk',identity),description='Colecao leve: autenticacao, diagnostico e consultas principais. Selecione o ambiente global SuccessFactors.'),
        collection=children,environments=dict(name='Base Environment',meta=dict(id=uid('env',identity)),data=env))
    attach_setup(lite)
    children=lite['collection']
    for path in [root/'environments/SuccessFactors.yaml',root/'environments/environment.example.json']:
        if path.suffix=='.yaml':
            environment=yaml.safe_load(path.read_text(encoding='utf-8'))
            environment['environments']['data'].update(SETUP_DEFAULTS)
            path.write_text(dump_yaml(environment),encoding='utf-8')
        else:
            environment=json.loads(path.read_text(encoding='utf-8'))
            environment.update(SETUP_DEFAULTS)
            path.write_text(json.dumps(environment,indent=2)+'\n',encoding='utf-8')
    def count(items):return sum(1 if 'method' in r else count(r.get('children',[])) for r in items)
    # Finish and verify the archive before removing any of the source files.
    if generated:
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name,path in source.items(): z.writestr(name,path.read_bytes())
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            for name,path in source.items(): assert z.read(name)==path.read_bytes()
        for path in source.values():
            assert path.resolve().is_relative_to(root/'collections')
            path.unlink()
    (root/identity).write_text(dump_yaml(lite),encoding='utf-8')
    manifest=dict(collections=1,requests=count(children),entities=len(ESSENTIAL)+2,entity_names=ESSENTIAL+['AutoDelegateDetail','AutoDelegateConfig'],files=[identity],optional_archive='optional/successfactors-complete.zip')
    (root/'catalog/lite-summary.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__': package(Path(__file__).resolve().parents[1])
