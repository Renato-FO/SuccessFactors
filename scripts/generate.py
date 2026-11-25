"""Generate generic Insomnia collections from a local OData v2 metadata file.

Only schema identifiers are consumed. Labels, defaults, annotations, URLs,
custom extensions and instance values are never copied to generated files.
"""
import argparse
import collections
import csv
import hashlib
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

SAP = '{http://www.successfactors.com/edm/sap}'
M = '{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}'
SCHEMA_URL = 'https://raw.githubusercontent.com/Kong/insomnia/develop/schemas/insomnia.schema.5.1.json'

# Public, standard API families. Configured template entities and extensions
# are deliberately excluded even if their runtime metadata is accessible.
STANDARD = set('''User UserAccount UserPermissions Photo PerPerson PerPersonal
PerEmail PerPhone PerAddressDEFLT PerNationalId PerEmergencyContacts
PerPersonRelationship PerPersonRelationshipInfo PerSocialAccount
EmpEmployment EmpEmploymentTermination EmpJob EmpJobRelationships
EmpCompensation EmpPayCompRecurring EmpPayCompNonRecurring EmpPayCompNonRecurringGroup
EmpEmploymentInformation EmpCostDistribution EmpCostDistributionItem
EmpWorkPermit EmpPensionPayout EmpJobInfo EmpEmploymentHigherDuty
EmpEmploymentConcurrent EmpGlobalAssignment EmpEmploymentWithCompanies
EmpTimeAccountBalance EmpTimeAccountPayout EmpTimeAccountPayoutRequest
FOCompany FOLocation FODepartment FODivision FOBusinessUnit FOCostCenter
FOJobCode FOJobFunction FOJobClassLocalDEFLT FOLegalEntityLocalDEFLT
FOPayGrade FOPayRange FOPayComponent FOPayComponentGroup FOPayGroup
FOFrequency FOEventReason FOEmployeeClass FOEmploymentType FOHolidayCalendar
FOWfConfig FOWfConfigStepApprover FOWfConfigStep FODynamicRole
FODynamicRoleAssignment FOCorporateAddressDEFLT FOTranslation
Position PositionRightToReturn PositionMatrixRelationship PositionRequisitionStatus
Picklist PicklistOption PicklistLabel PickListV2 PickListValueV2
Currency Country Territory TimeZone LanguageList Locale
JobRequisition JobRequisitionLocale JobRequisitionPosting JobRequisitionGroupOperator
JobRequisitionOperator JobRequisitionTeam JobRequisitionPostingFieldControls
JobApplication JobApplicationStatus JobApplicationStatusLabel
JobApplicationStatusAuditTrail JobApplicationInterview JobApplicationAssessmentOrder
JobApplicationOnboardingData JobApplicationQuestionResponse JobApplicationAttachment
Candidate CandidateLight CandidateProfileExtension CandidateProfileConversionInfo
CandidateTags CandidateTag CandidateMarketingConsent CandidateConsent
InterviewCentral InterviewOverallAssessment InterviewIndividualAssessment
InterviewQuestionEntity InterviewAssessment InterviewScheduling
OfferLetter JobOffer JobOfferApprover JobOfferLocale JobReqFwdCandidates
TalentPool TalentPoolCandidate JobProfile JobProfileLocalizedData
JobFamily JobRole JobLocations JobCodeEntity JobFunctionEntity
CompetencyEntity CompetencyContent CompetencyBehavior SkillEntity SkillContent
SkillProfile SkillProficiency SkillProficiencyLevel SkillMappingEntity
RoleSkillMappingEntity RoleCompetencyMappingEntity FamilyCompetencyMappingEntity
CertificationEntity CertificationContent EducationDegreeEntity EducationMajorEntity
WfRequest WfRequestStep WfRequestStepApprover WfRequestComments WfRequestParticipator
WorkflowAllowedActionList WorkflowConfig WorkflowStep WorkflowPendingData
Attachment DocumentGenerationTemplate DocumentGenerationGroup
DocumentGenerationTemplateMapping DocumentGenerationUserPermission
DynamicGroup DynamicRole DynamicRoleAssignment DGField DGFilter DGPeoplePool
RBPRole RBPGroup RBPUserToGroup RBPBasicPermission RBPUser RBPGroupToRole
PermissionRole PermissionGroup RolePermission RolePermissionAssignment
AlertMessage AlertNotification AlertType Todo TodoEntry TodoCategory
EmailTemplate EmailTrigger ThemeConfig UserSearch UserAccountInfo
ExternalUser ExtPersonalInfo ExtEmailInfo ExtPhoneInfo ExtAddressInfo
PaymentInformationV3 PaymentInformationDetailV3 PaymentInformationDetailV3OneTime
PayScaleArea PayScaleType PayScaleGroup PayScaleLevel PayScalePayComponent
RecurringDeduction NonRecurringDeduction OneTimeDeduction RecurringDeductionItem
DeductionScreenId SavingsAccountDeductionDetails SpotAwardProgram
SpotAward SpotAwardBudget SpotAwardProgramAdvancedSettings SpotAwardGuideline
OneTimePayment PayComponent PayComponentGroup PayrollConfiguration
PayrollSystemConfiguration PayrollConfigurationCategory PayrollUnifiedConfiguration
EmployeeTime EmployeeTimeGroup EmployeeTimeGroupItem EmployeeTimeCalendar
EmployeeTimeValuationResult EmployeeTimeValuationResultItem
EmployeeTimeSheet EmployeeTimeSheetEntry EmployeeTimeSheetData
TimeAccount TimeAccountDetail TimeAccountType TimeAccountTypeAccrual
TimeAccountPurchase TimeAccountPayout TimeAccountPayoutProfile
TimeAccountPostingRule TimeAccountSnapshot TimeAccountProcessSimulator
TimeType TimeTypeProfile TimeTypeProfileTimeType TimeProfile
TimeRecordingProfile TimeRecordingVariant TimeRecordingAdmissibility
TimeRecordingCalendar TimeRecording TimeRecordingEvent TimeEvent
TimeEventType TimeEventTypeGroup TimeEventPair TimeEventPairingStatus
TimeCollector TimeContainer TimeValuation TimeValuationResult TimeValuationPeriod
TimeOffRequesting TimeManagementTerminationEndHandlingConfiguration
TimeManagementTerminationEndHandlingLegalEntityConfiguration
TemporaryTimeInformation ExternalTimeData ExternalTimeRecord
ExternalTimeRecordStatus AllowanceRecording AbsenceCountingMethod
WorkSchedule WorkScheduleDay WorkScheduleDayModel WorkScheduleDayModelAssignment
WorkScheduleDayModelVariant WorkScheduleDayModelVariantAssignment
WorkScheduleDayModelSegment WorkScheduleDayModelSegmentVariant
Holiday HolidayCalendar HolidayAssignment HolidayCategory
ShiftClassification ShiftClassificationAssignment
AccrualRule AccrualCalculationBase AccrualCalculationAccountTypeBase
Period Periods PeriodEndProcessingRule
SimpleGoal GoalAchievements GoalEnum GoalPlanTemplate GoalPlanTemplateInfo
GoalPlanTemplateLink ContinuousPerformanceActivity ContinuousPerformanceAchievement
ContinuousPerformanceFeedback ContinuousPerformanceUserPermission
CalibrationSession CalibrationSessionReviewer CalibrationSessionSubject
MentoringProgram MentoringProgramParticipantInfo MentoringProgramMatchedParticipant
MentoringProgramParticipation MentoringProgramMatch
DevLearning LearningActivity LearningActivityTemplate LearningActivityCompetency
SuccessionNomination SuccessionNominationHistory SuccessionPosition
TalentRating TalentRatingHistory TalentCard TalentCardConfig
FormHeader FormContent FormRouteMap FormRouteStep FormRouteSubStep
FormIntroductionSection FormObjectiveSection FormCompetencySection
FormObjective FormCompetency FormCompetencyBehavior FormObjectiveOtherDetails
FormObjectiveOtherDetailsItemValueCell FormBehaviorRatingComment
FormPMReviewContentDetail FormJobRole Form360ParticipantSection
Form360ParticipantColumn Form360ParticipantConfig FormFolder
PerformancePotentialMatrix PerformancePotentialMatrixCell
ONB2Process ONB2ProcessTask ONB2ProcessTrigger ONB2ProcessStatus
ONB2DataCollectionUserConfig ONB2ResponsibleGroup ONB2EquipmentType
ONB2BuddyActivity ONB2MeetingActivity ONB2UsefulLinkActivity
ONB2NewHireTask ONB2NewHireActivity ONB2OffboardingActivitiesConfig
OnboardingCandidateInfo ComplianceDocumentFlow
FOBusinessUnitTranslation FODepartmentTranslation FODivisionTranslation
FOCompanyTranslation FOLocationTranslation FOJobCodeTranslation
UpsertResult InnerMessage BatchResult ODataAuditLog ODataAuditLogDetail
'''.split())

def is_standard(name):
    return name in STANDARD or bool(re.fullmatch(
        r'(?:LegalEntity|PerGlobalInfo|FOJobClassLocal|FOLegalEntityLocal|'
        r'PaymentInformationDetailV3|JobClassification|EmployeeTime|TimeType)[A-Z]{3}', name)) or bool(re.fullmatch(r'Benefit[A-Za-z]+', name))

def clean_name(name):
    return bool(re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name)) and not re.search(r'cust_|custom|extension', name, re.I)

def uid(prefix, value):
    return prefix + '_' + hashlib.sha256(value.encode()).hexdigest()[:32]

def category(name):
    if name.startswith('Benefit'): return '08-Beneficios'
    if name.startswith(('Candidate','JobReq','JobApp','Interview','Offer','JobOffer')): return '09-Recrutamento'
    if name.startswith(('ONB','Onboard','Compliance')): return '10-Onboarding'
    if name.startswith(('Time','EmployeeTime','WorkSchedule','Holiday','ExternalTime','EmpTime','TemporaryTime','Allowance','Accrual','Period','Shift','Absence')): return '07-Tempo-e-Ausencias'
    if name.startswith(('Pay','EmpPay','EmpComp','SpotAward','Recurring','NonRecurring','OneTime','Deduction','Savings')): return '06-Remuneracao-e-Folha'
    if name.startswith(('Form','Goal','SimpleGoal','Continuous','Calibration','Performance')): return '11-Desempenho-e-Metas'
    if name.startswith(('Mentoring','Dev','Learning','Succession','Talent')): return '12-Talentos-e-Desenvolvimento'
    if name.startswith(('Wf','Workflow','FOWf')): return '13-Workflows'
    if name.startswith(('RBP','Permission','RolePermission','Dynamic','DG')): return '14-Permissoes-e-Grupos'
    if name.startswith(('Per','ExtPersonal','ExtEmail','ExtPhone','ExtAddress')): return '02-Pessoas-e-Dados-Pessoais'
    if name.startswith(('User','Photo','ExternalUser')): return '01-Usuarios-e-Perfil'
    if name.startswith('Emp'): return '03-Vinculos-e-Cargos'
    if name.startswith(('FO','Position','LegalEntity')): return '04-Estrutura-Organizacional'
    if name.startswith(('Job','Skill','Competency','Role','Family','Certification','Education')): return '05-Cargos-e-Competencias'
    if name.startswith(('Pick','Country','Currency','Territory','TimeZone','Language','Locale')): return '15-Listas-e-Localizacao'
    return '16-Plataforma-e-Documentos'

def attr(node, name):
    return node.get(SAP+name, '')

def literal(typ, value='REPLACE_ME'):
    if typ == 'Edm.String': return "'"+value.replace("'", "''")+"'"
    if typ == 'Edm.DateTime': return "datetime'2000-01-01T00:00:00'"
    if typ == 'Edm.DateTimeOffset': return "datetimeoffset'2000-01-01T00:00:00Z'"
    if typ == 'Edm.Guid': return "guid'00000000-0000-0000-0000-000000000000'"
    if typ == 'Edm.Boolean': return 'false'
    if typ == 'Edm.Int64': return '0L'
    if typ == 'Edm.Decimal': return '0M'
    if typ == 'Edm.Single': return '0f'
    if typ == 'Edm.Double': return '0d'
    if typ == 'Edm.Time': return "time'PT0H0M0S'"
    if typ == 'Edm.Binary': return "binary''"
    return '0'

def json_value(typ):
    if typ in ('Edm.DateTime','Edm.DateTimeOffset'): return '/Date(946684800000)/'
    if typ == 'Edm.Boolean': return False
    if typ in ('Edm.Decimal','Edm.Int64'): return '0'
    if typ.startswith('Edm.') and typ not in ('Edm.String','Edm.Guid','Edm.Binary','Edm.Time'): return 0
    if typ == 'Edm.Guid': return '00000000-0000-0000-0000-000000000000'
    if typ.startswith('Collection('): return []
    if not typ.startswith('Edm.'): return {}
    return 'REPLACE_ME'

BASE_ENV = dict(base_url='https://api.example.successfactors.com',access_token='',
    btp_token_url='',btp_client_id='',btp_client_secret='',btp_access_token='',
    destination_service_url='',destination_name='YOUR_DESTINATION_NAME',
    sf_company_id='',sf_client_id='',saml_assertion='',page_size='20',skip='0',
    as_of_date='2000-01-01',from_date='2000-01-01',to_date='2000-12-31',
    user_id='USER_ID',person_id_external='PERSON_ID',company_code='COMPANY_CODE',location_code='LOCATION_CODE')

def param(name,value,disabled=False): return dict(name=name,value=str(value),disabled=disabled)

def req(identity,name,path,method='GET',params=None,body=None,description='',auth=None,after=None):
    r = dict(name=name,url='{{ _.base_url }}'+path,method=method,
        meta=dict(id=uid('req',identity),description=description),
        authentication=auth if auth is not None else dict(type='bearer',token='{{ _.access_token }}',prefix='Bearer'),
        headers=[dict(name='Accept',value='application/json')],parameters=params or [])
    if body is not None:
        r['body']=dict(mimeType='application/json',text=json.dumps(body,indent=2,ensure_ascii=False))
        r['headers'].append(dict(name='Content-Type',value='application/json'))
    if after: r['scripts']=dict(afterResponse=after)
    return r

def folder(identity,name,children,description=''):
    return dict(name=name,meta=dict(id=uid('fld',identity),description=description),children=children)

def auth_folder(identity):
    save = lambda field: f"const data = insomnia.response.json();\nif (!data.access_token) throw new Error('Token ausente na resposta');\ninsomnia.globals.set('{field}', data.access_token);"
    btp=req(identity+'/btp','01 — Token BTP','',method='POST',auth=dict(type='basic',username='{{ _.btp_client_id }}',password='{{ _.btp_client_secret }}'),description='Service key do Destination Service: url + /oauth/token, clientid e clientsecret.',after=save('btp_access_token'))
    btp['url']='{{ _.btp_token_url }}'
    btp['body']=dict(mimeType='application/x-www-form-urlencoded',params=[param('grant_type','client_credentials')])
    btp['headers']=[dict(name='Content-Type',value='application/x-www-form-urlencoded')]
    dest=req(identity+'/destination','02 — Token SuccessFactors via Destination','',auth=dict(type='bearer',token='{{ _.btp_access_token }}',prefix='Bearer'),description='destination_service_url = uri da service key. Salva automaticamente access_token global.',after="const data = insomnia.response.json();\nconst token = (data.authTokens || []).find(t => t.value && !t.error);\nif (!token) throw new Error('Destination sem token utilizável');\ninsomnia.globals.set('access_token', token.value);")
    dest['url']='{{ _.destination_service_url }}/destination-configuration/v1/destinations/{{ _.destination_name }}'
    direct=req(identity+'/saml','Alternativa — Token direto SAML','/oauth/token',method='POST',auth={},after=save('access_token'),description='Requer assertion SAML assinada em Base64. sf_company_id é o ID do tenant; sf_client_id é a API Key OAuth.')
    direct['body']=dict(mimeType='application/x-www-form-urlencoded',params=[param(k,v) for k,v in dict(company_id='{{ _.sf_company_id }}',client_id='{{ _.sf_client_id }}',grant_type='urn:ietf:params:oauth:grant-type:saml2-bearer',assertion='{{ _.saml_assertion }}').items()])
    direct['headers']=[dict(name='Content-Type',value='application/x-www-form-urlencoded')]
    connect=req(identity+'/connect','Conectar — BTP + SuccessFactors em uma chamada','',method='POST',auth=btp['authentication'],description='Preencha o ambiente global SuccessFactors e selecione-o na coleção. Obtém token BTP e consulta a Destination automaticamente. Os tokens ficam disponíveis para todas as coleções que usam esse ambiente global.',after="""const data = insomnia.response.json();
if (!data.access_token) throw new Error('Token BTP ausente');
insomnia.globals.set('btp_access_token', data.access_token);
const service = String(insomnia.variables.get('destination_service_url') || '').replace(/\\/$/, '');
const name = insomnia.variables.get('destination_name');
if (!service || !name) throw new Error('Preencha destination_service_url e destination_name');
const response = await new Promise((resolve, reject) => {
  insomnia.sendRequest({
    url: service + '/destination-configuration/v1/destinations/' + encodeURIComponent(name),
    method: 'GET',
    header: { Authorization: 'Bearer ' + data.access_token, Accept: 'application/json' }
  }, (error, response) => error ? reject(error) : resolve(response));
});
if (response.code !== 200) throw new Error('Destination retornou HTTP ' + response.code);
const destination = response.json();
const token = (destination.authTokens || []).find(t => t.value && !t.error);
if (!token) throw new Error('Destination não retornou token utilizável');
insomnia.globals.set('access_token', token.value);
insomnia.test('Token SuccessFactors obtido', () => insomnia.expect(token.value).to.be.a('string').and.not.empty);
""")
    connect['url']=btp['url'];connect['body']=btp['body'];connect['headers']=btp['headers']
    return folder(identity+'/auth','00 — Autenticacao',[connect,btp,dest,direct])

def key_capture(name,keys,props):
    types={k:props[k]['type'] for k in keys}
    return '''const data = insomnia.response.json();
insomnia.test('HTTP 200', () => insomnia.expect(insomnia.response.code).to.eql(200));
const first = data.d && data.d.results && data.d.results[0];
const types = TYPES;
if (first && Object.keys(types).length && Object.keys(types).every(k => first[k] !== undefined && first[k] !== null)) {
  const literal = (type, value) => {
    if (type === 'Edm.String') return "'" + String(value).replaceAll("'", "''") + "'";
    if (type === 'Edm.DateTime' || type === 'Edm.DateTimeOffset') {
      const m = String(value).match(/^\\/Date\\((-?\\d+)(?:[+-]\\d{4})?\\)\\/$/);
      const iso = new Date(m ? Number(m[1]) : value).toISOString().replace('.000Z', type === 'Edm.DateTime' ? '' : 'Z');
      return (type === 'Edm.DateTime' ? 'datetime' : 'datetimeoffset') + "'" + iso + "'";
    }
    if (type === 'Edm.Guid') return "guid'" + value + "'";
    return String(value) + ({'Edm.Int64':'L','Edm.Decimal':'M','Edm.Single':'f','Edm.Double':'d'}[type] || '');
  };
  insomnia.environment.set('key_NAME', Object.entries(types).map(([k,t]) => k + '=' + literal(t,first[k])).join(','));
}
if (data.d && data.d.__next) insomnia.environment.set('next_page_url', data.d.__next);
'''.replace('TYPES',json.dumps(types)).replace('key_NAME','key_'+name)

def build(args):
    root=ET.parse(args.metadata).getroot()
    types={t.get('Name'):t for t in root.findall('.//{*}EntityType')}
    all_sets={s.get('Name'):s for s in root.findall('.//{*}EntitySet')}
    sets={n:s for n,s in all_sets.items() if is_standard(n) and clean_name(n)}
    type_to_set={s.get('EntityType'):n for n,s in sets.items()}
    associations={a.get('Name'):{e.get('Role'):e.attrib for e in a.findall('{*}End')} for a in root.findall('.//{*}Association')}
    entities=[]
    for name,s in sorted(sets.items()):
        t=types[s.get('EntityType').split('.')[-1]]
        props={p.get('Name'):dict(type=p.get('Type'),nullable=p.get('Nullable','true')=='true',required=attr(p,'required')=='true',creatable=attr(p,'creatable')=='true',updatable=attr(p,'updatable')=='true',upsertable=attr(p,'upsertable')=='true',filterable=attr(p,'filterable')=='true') for p in t.findall('{*}Property') if clean_name(p.get('Name',''))}
        keys=[k.get('Name') for k in t.findall('{*}Key/{*}PropertyRef')]
        if not all(k in props for k in keys): continue
        nav=[]
        for n in t.findall('{*}NavigationProperty'):
            if not clean_name(n.get('Name','')): continue
            end=associations.get(n.get('Relationship','').split('.')[-1],{}).get(n.get('ToRole'),{})
            target=type_to_set.get(end.get('Type'))
            if target: nav.append(dict(name=n.get('Name'),target=target,many=end.get('Multiplicity')=='*'))
        entities.append(dict(name=name,area=category(name),keys=keys,properties=props,navigations=nav,operations={op:attr(s,op)=='true' for op in ['creatable','updatable','upsertable','deletable']},effective_dated='startDate' in props or 'effectiveStartDate' in props))
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    def write(path,data):
        p=out/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data,encoding='utf-8')
    env_template=dict(BASE_ENV,next_page_url='')
    collections_out=[]
    def collection(path,name,children,env=None):
        identity=path
        doc=dict(type='collection.insomnia.rest/5.0',schema_version='5.1',name=name,meta=dict(id=uid('wrk',identity),description='Selecione o ambiente global SuccessFactors. Modelos genericos OData v2; ajuste parametros e permissoes antes de usar.'),collection=[auth_folder(identity)]+children,environments=dict(name='Base Environment',meta=dict(id=uid('env',identity)),data=dict(next_page_url='',**(env or {}))))
        write(path,yaml.safe_dump(doc,allow_unicode=True,sort_keys=False,width=110))
        def count(items): return sum(1 if 'method' in x else count(x.get('children',[])) for x in items)
        collections_out.append(dict(file=path,name=name,requests=count(doc['collection'])))
    read_groups=collections.defaultdict(list);write_groups=collections.defaultdict(list)
    catalog=[]
    for e in entities:
        name=e['name'];props=e['properties'];keys=e['keys']; key_var='key_'+name
        key=','.join(k+'='+literal(props[k]['type']) for k in keys)
        env={key_var:key}
        path='/odata/v2/'+name
        keyed=path+'({{ _.'+key_var+' }})'
        common=[param('$format','json')]
        selected=','.join(dict.fromkeys(keys+list(props)[:8]))
        desc='Chaves: '+(', '.join(k+' ('+props[k]['type']+')' for k in keys) or 'nenhuma')+'. Execute Listar para preencher automaticamente '+key_var+'. Campos e permissoes podem variar por tenant.'
        reads=[req(name+'/list','01 — Listar',path,params=common+[param('$top','{{ _.page_size }}'),param('$skip','{{ _.skip }}'),param('$select',selected,True)],description=desc,after=key_capture(name,keys,props)),
            req(name+'/select','02 — Selecionar campos',path,params=common+[param('$top','{{ _.page_size }}'),param('$select',selected)],description=desc)]
        if keys:
            reads.append(req(name+'/key','03 — Buscar por chave',keyed,params=common,description=desc))
        filters=[k for k in keys if props[k]['filterable']] or [k for k,p in props.items() if p['filterable']][:1]
        if filters:
            reads.append(req(name+'/filter','04 — Filtrar',path,params=common+[param('$top','{{ _.page_size }}'),param('$filter',' and '.join(k+' eq '+literal(props[k]['type']) for k in filters))],description='Substitua REPLACE_ME e os valores de exemplo. Use literais OData adequados ao tipo.'))
        reads.append(req(name+'/count','05 — Contar',path+'/$count',description='Retorna texto com a contagem. Suporte depende da entidade.'))
        reads[-1]['headers']=[dict(name='Accept',value='text/plain')]
        if e['effective_dated']:
            reads.extend([req(name+'/asof','06 — Data de referencia',path,params=common+[param('$top','{{ _.page_size }}'),param('asOfDate','{{ _.as_of_date }}')],description='Consulta temporal; ajuste as_of_date.'),req(name+'/history','07 — Historico por periodo',path,params=common+[param('$top','{{ _.page_size }}'),param('fromDate','{{ _.from_date }}'),param('toDate','{{ _.to_date }}')],description='Consulta temporal; ajuste from_date e to_date.')])
        navs=[]
        for n in e['navigations']:
            navs.append(req(name+'/nav/'+n['name'],'Navegar — '+n['name'],keyed+'/'+n['name'],params=common+([param('$top','{{ _.page_size }}')] if n['many'] else []),description='Destino: '+n['target']+'. '+desc))
            navs.append(req(name+'/expand/'+n['name'],'Expandir — '+n['name'],path,params=common+[param('$top','1'),param('$expand',n['name'])],description='Destino: '+n['target']+'. Expansao limitada a um registro principal.'))
        if navs: reads.append(folder(name+'/navs','Relacionamentos',navs))
        read_groups[e['area']].append((folder(name+'/read',name,reads),env))
        writes=[]
        for op,method,label in [('creatable','POST','Criar'),('updatable','MERGE','Atualizar'),('upsertable','POST','Upsert')]:
            if not e['operations'][op]: continue
            field_flag=op
            fields=[k for k,p in props.items() if p[field_flag] and (p['required'] or k in keys)]
            if op!='creatable': fields=list(dict.fromkeys(keys+fields))
            if not fields: fields=[k for k,p in props.items() if p[field_flag]][:1]
            payload={k:json_value(props[k]['type']) for k in fields}
            endpoint=path if op=='creatable' else keyed
            if op=='upsertable':
                endpoint='/odata/v2/upsert'
                payload={'__metadata':{'uri':name},**payload}
                payload=[payload]
            writes.append(req(name+'/'+op,label,endpoint,method=method,params=common,body=payload,description='MODELO DE ESCRITA. Revise chaves, campos obrigatorios e regras do tenant. Valores sao exemplos ficticios. '+desc))
        if e['operations']['deletable'] and keys:
            writes.append(req(name+'/delete','Excluir',keyed,method='DELETE',description='Exclui o registro identificado pela chave. '+desc))
        if writes: write_groups[e['area']].append((folder(name+'/write',name,writes),env))
        catalog.append(e)
    for kind,groups in [('Leitura',read_groups),('Escrita',write_groups)]:
        for area,items in sorted(groups.items()):
            for i in range(0,len(items),35):
                chunk=items[i:i+35]; suffix=f'{i//35+1:02d}'
                env={k:v for _,d in chunk for k,v in d.items()}
                collection(f'collections/{area}/{kind}-{suffix}.yaml',f'SuccessFactors | {area[3:]} | {kind} {suffix}',[x for x,_ in chunk],env)
    # Standard function imports: only technical signatures, never runtime defaults.
    functions=[];function_requests=[]
    for f in root.findall('.//{*}FunctionImport'):
        name=f.get('Name','')
        if not clean_name(name): continue
        params=[dict(name=p.get('Name'),type=p.get('Type')) for p in f.findall('{*}Parameter') if clean_name(p.get('Name',''))]
        if any(not p['type'].startswith(('Edm.','Collection(Edm.')) and p['type'].split('.')[-1] not in sets for p in params): continue
        method=f.get(M+'HttpMethod','GET');payload=attr(f,'support-payload')=='true'
        values={p['name']:json_value(p['type']) for p in params}
        q= [param('$format','json')]+([] if payload else [param(p['name'],literal(p['type'])) for p in params])
        r=req('function/'+name,name,'/odata/v2/'+name,method=method,params=q,body=values if payload else None,description='Operacao OData: '+name+'. Revise parametros e efeito antes de executar. '+('Parametros JSON no corpo.' if payload else 'Parametros tipados em query string.'))
        function_requests.append(r);functions.append(dict(name=name,method=method,payload=payload,parameters=params))
    collection('collections/17-Operacoes/Funcoes.yaml','SuccessFactors | Operacoes OData',function_requests)
    diagnostics=[req('meta','Metadata XML','/odata/v2/$metadata'),req('service','Catalogo do servico','/odata/v2/',params=[param('$format','json')])]
    diagnostics[0]['headers']=[dict(name='Accept',value='application/xml')]
    next_page=req('next','Proxima pagina','',description='Execute Listar primeiro. next_page_url recebe d.__next da resposta. Verifique o host antes de enviar.')
    next_page['url']='{{ _.next_page_url }}';diagnostics.append(next_page)
    for entity,field,var in [('FOCompany','externalCode','company_code'),('FOLocation','externalCode','location_code'),('User','userId','user_id'),('EmpJob','userId','user_id'),('PerPerson','personIdExternal','person_id_external')]:
        if entity in sets:
            diagnostics.append(req('quick/'+entity,entity+' — Consulta parametrizada','/odata/v2/'+entity,params=[param('$format','json'),param('$filter',field+" eq '{{ _."+var+" }}'"),param('$top','20')]))
    collection('collections/00-Inicio/Diagnostico-e-Consultas.yaml','SuccessFactors | Inicio e diagnostico',diagnostics)
    write('catalog/entities.json',json.dumps(catalog,indent=2,ensure_ascii=False)+'\n')
    write('catalog/functions.json',json.dumps(functions,indent=2,ensure_ascii=False)+'\n')
    write('environments/environment.example.json',json.dumps(env_template,indent=2)+'\n')
    global_environment=dict(type='environment.insomnia.rest/5.0',schema_version='5.1',name='SuccessFactors',meta=dict(id=uid('wrk','global-successfactors')),environments=dict(name='Base Environment',meta=dict(id=uid('env','global-successfactors')),data=env_template))
    write('environments/SuccessFactors.yaml',yaml.safe_dump(global_environment,allow_unicode=True,sort_keys=False))
    index=out/'catalog/entities.csv'
    with index.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.writer(handle);writer.writerow(['area','entity','keys','properties','relationships','create','update','upsert','delete'])
        for e in catalog: writer.writerow([e['area'],e['name'],','.join(e['keys']),len(e['properties']),len(e['navigations']),*[e['operations'][k] for k in ['creatable','updatable','upsertable','deletable']]])
    summary=dict(entities=len(catalog),functions=len(functions),relationships=sum(len(e['navigations']) for e in catalog),requests=sum(c['requests'] for c in collections_out),collections=len(collections_out),files=collections_out)
    write('catalog/summary.json',json.dumps(summary,indent=2)+'\n')
    schema=urllib.request.urlopen(SCHEMA_URL).read().decode()
    write('schemas/insomnia.schema.5.1.json',schema)
    print(json.dumps({k:v for k,v in summary.items() if k!='files'},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata',required=True,type=Path)
    parser.add_argument('--out',default='.')
    build(parser.parse_args())
