"""Native Setup integration; the same runtime is embedded in collection hooks."""
from pathlib import Path
from generate import uid

ROOT=Path(__file__).resolve().parent
SETUP_DEFAULTS = {
    'setup_scope':'collection','setup_private_environment':False,'setup_enabled':False,
    'destination_service_key':'','setup_api_path':'/odata/v2','destination_user_token':'','entity_name':'',
    'btp_token_expires_at':0,'destination_expires_at':0,'destination_authorization':'',
    'cis_service_key':'','cis_token_url':'','cis_client_id':'','cis_client_secret':'',
    'cis_access_token':'','cis_accounts_url':'','cis_token_expires_at':0,
    'global_account_guid':'','subaccount_guid':'','btp_region':'',
    'cf_api_url':'','cf_access_token':'','cf_org_guid':'','cf_space_guid':'',
    'cf_instance_guid':'','cf_binding_guid':'','cf_authorization_url':'','cf_token_url':'',
    'cf_oauth_client_id':'','cf_oauth_client_secret':'','cf_oauth_redirect_url':'',
}

STEPS = [
    ('destinations-subaccount','01 — Conectar BTP e listar Destinations da subconta','Use destination_service_key ou as quatro variaveis BTP. Resultado resumido em setup_destinations_subaccount.'),
    ('destinations-instance','02 — Listar Destinations da instancia','Resultado em setup_destinations_instance. A resolucao por nome prioriza a instancia quando ha nomes repetidos.'),
    ('destination','03 — Aplicar Destination selecionada','Preencha destination_name. Salva URL, autenticacao, tokens e habilita renovacao automatica no Environment ativo.'),
    ('metadata','04 — Consultar metadata e entidades','Usa setup_api_path. Salva apenas os nomes das EntitySets em setup_entities. As consultas de negocio existentes continuam sendo OData v2.'),
    ('entity','Consultar entidade selecionada','Opcional. Preencha entity_name a partir de setup_entities. GET generico sobre setup_api_path, sem adaptar schemas, filtros ou paginacao entre protocolos.'),
    ('cis-global','05 — CIS: consultar Global Account da credencial','Opcional. Requer cis_service_key (plano central) ou variaveis CIS. Nao lista todas as Global Accounts de um login humano.'),
    ('cis-subaccounts','06 — CIS: listar subcontas acessiveis','Opcional. Salva setup_subaccounts. Escolha subaccount_guid no Environment.'),
    ('cis-subaccount','07 — CIS: aplicar subconta e regiao','Opcional. Busca subaccount_guid. Guarda a regiao retornada, sem montar hosts por substituicao de BR10/US10/EU10.'),
    ('cf-info','08 — CF: descobrir endpoints OAuth','Opcional. Configure cf_api_url da subconta/regiao. Descobre os links de login; nao realiza SSO pelo script.'),
    ('cf-native-login','09 — CF: login OAuth2 nativo e organizacoes','Opcional. Configure o cliente OAuth registrado e use Auth > Fetch Tokens no Insomnia. Redirecionamento e permissoes dependem do IdP. Se o SDK nao expuser o token, copie-o para cf_access_token.'),
    ('cf-orgs','10 — CF: listar organizacoes','Opcional. Usa cf_access_token. Escolha cf_org_guid a partir de setup_cf_orgs.'),
    ('cf-spaces','11 — CF: listar spaces','Opcional. Escolha cf_space_guid a partir de setup_cf_spaces.'),
    ('cf-instances','12 — CF: descobrir instancias Destination','Opcional. Filtra os planos do offering destination no space selecionado. Escolha cf_instance_guid.'),
    ('cf-bindings','13 — CF: listar service keys existentes','Opcional. Consulta somente keys da instancia selecionada. Escolha cf_binding_guid. Nao cria nem modifica recursos BTP.'),
    ('cf-key','14 — CF: importar service key selecionada','Opcional. Requer permissao para ler credenciais. Salva somente os campos de conexao no Environment privado ativo. Depois execute 01 e 03.'),
]

def attach_setup(doc):
    runtime=(ROOT/'insomnia/setup-runtime.js').read_text(encoding='utf-8')
    doc['scripts']={
        'preRequest':runtime+"\nconst action = insomnia.variables.get('setup_action');\nif (action) await SFSetup.prepare(action);\nelse if (!insomnia.variables.get('setup_skip_refresh')) await SFSetup.beforeBusiness();\n",
        'afterResponse':runtime+"\nconst action = insomnia.variables.get('setup_action');\nif (action) await SFSetup.complete(action);\n",
    }
    children=[]
    for action,name,description in STEPS:
        # The pre-request hook replaces this reserved, non-routable URL.
        # Never interpolate the service URL before Setup has discovered it.
        request=dict(name='Executar',url='https://setup.invalid/',method='GET',
            meta=dict(id=uid('req','setup/'+action),description=description),authentication={},headers=[],parameters=[])
        if action=='cf-native-login':
            request['authentication']=dict(type='oauth2',grantType='authorization_code',
                authorizationUrl='{{ _.cf_authorization_url }}',accessTokenUrl='{{ _.cf_token_url }}',
                clientId='{{ _.cf_oauth_client_id }}',clientSecret='{{ _.cf_oauth_client_secret }}',
                redirectUrl='{{ _.cf_oauth_redirect_url }}',usePkce=True,useDefaultBrowser=True)
        children.append(dict(name=name,meta=dict(id=uid('fld','setup/'+action),description=description),
            environment=dict(setup_action=action),children=[request]))
    doc['collection']=[item for item in doc['collection'] if item.get('name')!='Setup']
    for item in doc['collection']:
        if item.get('name')=='00 — Autenticacao': item['environment']={'setup_skip_refresh':True}
    doc['collection'].insert(0,dict(name='Setup',meta=dict(id=uid('fld','native-setup'),description='Configuracao nativa por cliente; selecione um Environment privado. Etapas CIS/CF sao opcionais.'),children=children))
    return doc
