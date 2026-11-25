// Embedded into native Insomnia scripts at build time. No plugin or local require.
const SFSetup = (() => {
  const URLClass = require('url').URL;
  const scope = insomnia.environment.get('setup_scope') || insomnia.globals.get('setup_scope') || 'collection';
  if (!['collection', 'global'].includes(scope)) throw new Error('setup_scope deve ser collection ou global');
  const store = scope === 'global' ? insomnia.globals : insomnia.environment;
  const get = key => store.get(key);
  const put = (key, value) => store.set(key, value);
  const enabled = value => value === true || value === 'true';
  const required = key => {
    const value = get(key);
    if (value === undefined || value === null || String(value).trim() === '') throw new Error('Preencha ' + key + ' no Environment privado ativo');
    return String(value).trim();
  };
  function guard() {
    if (!enabled(get('setup_private_environment'))) throw new Error('Crie e selecione um Environment PRIVADO; defina setup_private_environment=true nele. O script nativo nao consegue verificar isPrivate.');
  }
  function url(value) {
    const parsed = new URLClass(String(value));
    if (parsed.protocol !== 'https:' || parsed.username || parsed.password || parsed.hash) throw new Error('Use uma URL HTTPS sem credenciais ou fragmento');
    return parsed;
  }
  const base = value => url(value).toString().replace(/\/$/, '');
  function join(root, path) { return base(root) + '/' + path.replace(/^\//, ''); }
  function json(value) { return typeof value === 'string' ? JSON.parse(value) : value; }
  const readArray = key => { const value = get(key); return value ? json(value) : []; };
  function status(response, label) {
    if (response.code < 200 || response.code >= 300) {
      const hint = response.code === 403 ? ' Confira escopos e papeis desta credencial.' : response.code === 401 ? ' Renove a sessao ou confira as credenciais.' : '';
      throw new Error(label + ': HTTP ' + response.code + '.' + hint);
    }
  }
  async function send(request, label) {
    const response = await new Promise((resolve, reject) => insomnia.sendRequest(request, (error, result) => error ? reject(new Error(label + ': falha de transporte')) : resolve(result)));
    status(response, label);
    return response.json();
  }
  function expiry(token, seconds) {
    const duration = Number(seconds);
    if (Number.isFinite(duration) && duration > 0) return Date.now() + duration * 1000;
    try {
      const payload = String(token).split('.')[1];
      const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
      const claims = JSON.parse(require('atob')(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')));
      return Number(claims.exp) > 0 ? Number(claims.exp) * 1000 : 0;
    } catch { return 0; }
  }
  const fresh = (token, until) => Boolean(token) && Number(until) > Date.now() + 60000;
  function importKey(kind, supplied) {
    const raw = supplied || get(kind === 'cis' ? 'cis_service_key' : 'destination_service_key');
    if (!raw) return;
    let credentials;
    try { const data = json(raw); credentials = data.credentials || data; }
    catch { throw new Error('Service key deve ser JSON valido'); }
    const c = credentials;
    if (kind !== 'cis' && get('subaccount_guid') && (c.subaccountid || c.uaa && c.uaa.subaccountid) && get('subaccount_guid') !== (c.subaccountid || c.uaa.subaccountid)) throw new Error('Service key pertence a outra subconta. Confira a selecao.');
    const uaa = c.uaa || c;
    const tokenUrl = join(uaa.url || c.url, '/oauth/token');
    const fields = kind === 'cis'
      ? {cis_token_url: tokenUrl, cis_client_id: uaa.clientid, cis_client_secret: uaa.clientsecret, cis_accounts_url: base(c.endpoints && c.endpoints.accounts_service_url)}
      : {btp_token_url: tokenUrl, btp_client_id: uaa.clientid, btp_client_secret: uaa.clientsecret, destination_service_url: base(c.uri)};
    if (Object.values(fields).some(v => !v)) throw new Error('Service key incompleta para ' + kind);
    const changed = Object.entries(fields).some(([k, v]) => get(k) !== v);
    Object.entries(fields).forEach(([k, v]) => put(k, v));
    if (supplied && kind !== 'cis') put('destination_service_key', '');
    if (changed) {
      put(kind === 'cis' ? 'cis_access_token' : 'btp_access_token', '');
      put(kind === 'cis' ? 'cis_token_expires_at' : 'btp_token_expires_at', 0);
      if (kind !== 'cis') { put('destination_expires_at', 0); put('access_token', ''); put('setup_enabled', false); }
    }
  }
  async function oauth(kind, force = false) {
    const prefix = kind === 'cis' ? 'cis' : 'btp';
    const tokenKey = prefix === 'cis' ? 'cis_access_token' : 'btp_access_token';
    const expiresKey = prefix + '_token_expires_at';
    const context = JSON.stringify([get(prefix + '_token_url'), get(prefix + '_client_id')]);
    if (!force && get(prefix + '_token_context') === context && fresh(get(tokenKey), get(expiresKey))) return get(tokenKey);
    const endpoint = base(required(prefix + '_token_url'));
    const response = await send({url: endpoint, method: 'POST',
      header: {'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json'},
      auth: {type: 'basic', basic: [{key: 'username', value: required(prefix + '_client_id')}, {key: 'password', value: required(prefix + '_client_secret')}]},
      body: {mode: 'urlencoded', urlencoded: [{key: 'grant_type', value: 'client_credentials'}]}}, 'OAuth ' + prefix);
    if (!response.access_token) throw new Error('OAuth nao retornou access_token');
    const until = expiry(response.access_token, response.expires_in);
    if (until && until <= Date.now()) throw new Error('OAuth retornou token expirado');
    put(tokenKey, response.access_token);
    put(expiresKey, until);
    put(prefix + '_token_context', context);
    return response.access_token;
  }
  function destinationContext() { return JSON.stringify([get('destination_service_url'), get('destination_name'), get('btp_client_id'), get('destination_user_token') || '']); }
  async function destinationHeaders() {
    const headers = {Authorization: 'Bearer ' + await oauth('btp'), Accept: 'application/json'};
    if (get('destination_user_token')) headers['X-User-Token'] = get('destination_user_token');
    return headers;
  }
  function applyDestination(data) {
    const config = data.destinationConfiguration;
    if (!config || !config.URL) throw new Error('Resposta sem destinationConfiguration.URL');
    if (config.ProxyType && config.ProxyType !== 'Internet') throw new Error('Esta collection usa conexao direta Internet. OnPremise/PrivateLink exige proxy apropriado; configuracao nao foi aplicada.');
    const type = config.Authentication || 'NoAuthentication';
    const selected = (data.authTokens || []).find(t => !t.error && (t.value || t.http_header && t.http_header.value));
    let authorization = '';
    if (type !== 'NoAuthentication') {
      if (!selected) throw new Error('Destination sem authToken utilizavel. Fluxos com usuario exigem destination_user_token e permissoes adequadas.');
      const header = selected.http_header;
      if (header && String(header.key).toLowerCase() === 'authorization') authorization = header.value;
      else if (selected.type && selected.value) authorization = selected.type + ' ' + selected.value;
      else throw new Error('Destination nao retornou um header Authorization utilizavel');
      if (!/^(Bearer|Basic)\s+\S+/i.test(authorization)) throw new Error('Tipo de autorizacao nao suportado pela collection');
    }
    const original = url(config.URL);
    if (original.search) throw new Error('Destination URL com query string: use uma URL base de servico');
    let endpoint = original.toString().replace(/\/$/, '');
    let apiPath = get('setup_api_path') || '/odata/v2';
    const match = endpoint.match(/^(.*)(\/odata\/v[24](?:\/.*)?)$/i);
    if (match) { endpoint = match[1]; apiPath = match[2]; }
    const until = selected ? expiry(selected.value, selected.expires_in) : Date.now() + 3600000;
    if (until && until <= Date.now()) throw new Error('Destination retornou token expirado');
    // Publish related state together only after validating the entire response.
    put('base_url', endpoint);
    put('setup_api_path', apiPath);
    put('destination_authentication', type);
    put('destination_authorization', authorization);
    put('access_token', /^Bearer\s/i.test(authorization) ? authorization.replace(/^Bearer\s+/i, '') : '');
    put('destination_expires_at', until);
    put('destination_token_context', destinationContext());
    put('setup_enabled', true);
  }
  async function ensureDestination(force = false) {
    if (!force && get('destination_token_context') === destinationContext() && Number(get('destination_expires_at')) > Date.now() + 60000) return;
    const endpoint = join(required('destination_service_url'), '/destination-configuration/v1/destinations/' + encodeURIComponent(required('destination_name')));
    const data = await send({url: endpoint, method: 'GET', header: await destinationHeaders()}, 'Resolver Destination');
    applyDestination(data);
  }
  function applyAuth(header) {
    insomnia.request.auth.update([], 'noauth');
    insomnia.request.removeHeader('Authorization');
    if (header) insomnia.request.addHeader({key: 'Authorization', value: header});
  }
  function cfToken() {
    const token = required('cf_access_token').replace(/^Bearer\s+/i, '');
    const until = expiry(token);
    if (until && until <= Date.now() + 60000) throw new Error('Sessao Cloud Foundry expirada. Renove via OAuth2 nativo ou atualize cf_access_token.');
    return token;
  }
  async function collect(data, root, headers) {
    const rows = Array.isArray(data) ? data : data.resources || data.value || [];
    if (!Array.isArray(rows)) throw new Error('Resposta de lista inesperada');
    const result = [...rows];
    let next = data.pagination && data.pagination.next && data.pagination.next.href;
    const seen = new Set();
    while (next) {
      const endpoint = new URLClass(next, base(root) + '/');
      if (endpoint.origin !== url(root).origin || seen.has(endpoint.href) || seen.size >= 100) throw new Error('Paginacao invalida ou fora do host da API');
      seen.add(endpoint.href);
      data = await send({url: endpoint.href, method: 'GET', header: headers}, 'Proxima pagina');
      result.push(...(data.resources || data.value || []));
      next = data.pagination && data.pagination.next && data.pagination.next.href;
    }
    return result;
  }
  async function prepare(action) {
    guard();
    let endpoint, header = {};
    if (action.startsWith('cis-')) {
      importKey('cis');
      header.Authorization = 'Bearer ' + await oauth('cis');
      endpoint = join(required('cis_accounts_url'), '/accounts/v1/' + (action === 'cis-global' ? 'globalAccount' : action === 'cis-subaccounts' ? 'subaccounts' : 'subaccounts/' + encodeURIComponent(required('subaccount_guid'))));
    } else if (action.startsWith('cf-')) {
      const root = required('cf_api_url');
      if (action !== 'cf-info' && action !== 'cf-native-login') header.Authorization = 'Bearer ' + cfToken();
      const path = {
        'cf-info': '/v3/info', 'cf-native-login': '/v3/organizations', 'cf-orgs': '/v3/organizations',
        'cf-spaces': '/v3/spaces?organization_guids=' + encodeURIComponent(get('cf_org_guid') || ''),
        'cf-bindings': '/v3/service_credential_bindings?type=key&service_instance_guids=' + encodeURIComponent(get('cf_instance_guid') || ''),
        'cf-key': '/v3/service_credential_bindings/' + encodeURIComponent(get('cf_binding_guid') || '') + '/details'
      }[action];
      if (action === 'cf-spaces') required('cf_org_guid');
      if (action === 'cf-bindings') required('cf_instance_guid');
      if (action === 'cf-key') {
        required('cf_binding_guid');
        if (!readArray('setup_cf_bindings').some(x => x.guid === get('cf_binding_guid') && x.instance_guid === get('cf_instance_guid'))) throw new Error('Liste e selecione uma service key da instancia escolhida antes de importar');
      }
      if (action === 'cf-instances') {
        required('cf_space_guid');
        const offerings = await collect(await send({url: join(root, '/v3/service_offerings?names=destination'), method: 'GET', header}, 'Service offerings'), root, header);
        if (!offerings.length) throw new Error('Offering destination nao disponivel para a sessao CF');
        const plans = await collect(await send({url: join(root, '/v3/service_plans?service_offering_guids=' + offerings.map(o => encodeURIComponent(o.guid)).join(',')), method: 'GET', header}, 'Service plans'), root, header);
        if (!plans.length) throw new Error('Nenhum service plan Destination acessivel');
        endpoint = join(root, '/v3/service_instances?space_guids=' + encodeURIComponent(required('cf_space_guid')) + '&service_plan_guids=' + plans.map(p => encodeURIComponent(p.guid)).join(','));
      } else endpoint = join(root, path);
    } else if (action === 'destinations-subaccount' || action === 'destinations-instance' || action === 'destination') {
      importKey('destination');
      header = await destinationHeaders();
      const path = action === 'destination' ? '/destinations/' + encodeURIComponent(required('destination_name')) : action === 'destinations-instance' ? '/instanceDestinations' : '/subaccountDestinations';
      endpoint = join(required('destination_service_url'), '/destination-configuration/v1' + path);
    } else if (action === 'metadata' || action === 'entity') {
      await ensureDestination();
      const entity = action === 'entity' ? required('entity_name') : '$metadata';
      if (action === 'entity' && !/^[A-Za-z_][A-Za-z0-9_.]*$/.test(entity)) throw new Error('entity_name deve conter apenas o nome tecnico de uma entidade');
      endpoint = join(required('base_url'), (get('setup_api_path') || '/odata/v2').replace(/\/$/, '') + '/' + entity);
      if (action === 'entity') endpoint += '?$top=' + encodeURIComponent(get('page_size') || '20');
      header.Authorization = get('destination_authorization');
    } else throw new Error('Etapa Setup desconhecida');
    insomnia.request.method = 'GET';
    insomnia.request.url = endpoint;
    if (action !== 'cf-native-login') applyAuth(header.Authorization);
    insomnia.request.addHeader({key: 'Accept', value: action === 'metadata' ? 'application/xml' : 'application/json'});
  }
  async function complete(action) {
    guard();
    status(insomnia.response, action);
    if (action === 'entity') return;
    if (action === 'metadata') {
      const parsed = await require('xml2js').parseStringPromise(insomnia.response.text(), {explicitArray: false, tagNameProcessors: [require('xml2js').processors.stripPrefix]});
      const found = new Set();
      function visit(node) {
        if (!node || typeof node !== 'object') return;
        for (const [key, value] of Object.entries(node)) {
          if (key === 'EntitySet') for (const entity of Array.isArray(value) ? value : [value]) if (entity.$ && entity.$.Name) found.add(entity.$.Name);
          if (key !== '$') (Array.isArray(value) ? value : [value]).forEach(visit);
        }
      }
      visit(parsed);
      put('setup_entities', JSON.stringify([...found].sort()));
      return;
    }
    const data = insomnia.response.json();
    if (action === 'destination') return applyDestination(data);
    if (action === 'cf-info') {
      const login = data.links && data.links.login && data.links.login.href;
      if (login) { put('cf_authorization_url', join(login, '/oauth/authorize')); put('cf_token_url', join(login, '/oauth/token')); }
      return;
    }
    if (action === 'cf-key') return importKey('destination', data);
    if (action === 'cis-global') {
      put('setup_global_accounts', JSON.stringify([{guid: data.guid, name: data.displayName, subdomain: data.subdomain}]));
      if (data.guid) put('global_account_guid', data.guid);
      return;
    }
    if (action === 'cis-subaccount') {
      if (data.region) put('btp_region', typeof data.region === 'string' ? data.region : data.region.name || '');
      if (data.subdomain) put('subaccount_subdomain', data.subdomain);
      return;
    }
    if (action === 'cf-native-login') {
      const auth = insomnia.request.auth.toJSON();
      const entry = (auth.oauth2 || []).find(p => p.key === 'accessToken');
      if (!entry || !entry.value) throw new Error('Token OAuth2 nao exposto pelo SDK. Copie o token obtido em Auth para cf_access_token do Environment privado e execute Listar organizacoes.');
      put('cf_access_token', entry.value);
    }
    const isCF = action.startsWith('cf-');
    const headers = isCF ? {Authorization: 'Bearer ' + cfToken()} : action.startsWith('cis-') ? {Authorization: 'Bearer ' + await oauth('cis')} : await destinationHeaders();
    const root = isCF ? required('cf_api_url') : action.startsWith('cis-') ? required('cis_accounts_url') : required('destination_service_url');
    const rows = await collect(data, root, headers);
    if (action.startsWith('destinations-')) {
      const level = action === 'destinations-instance' ? 'instance' : 'subaccount';
      // Only non-sensitive display fields are retained, never passwords returned by list APIs.
      put('setup_destinations_' + level, JSON.stringify(rows.map(d => ({name: d.Name, url: d.URL, authentication: d.Authentication, proxy: d.ProxyType}))));
    } else if (action === 'cis-subaccounts') {
      put('setup_subaccounts', JSON.stringify(rows.map(s => ({guid: s.guid, name: s.displayName, region: s.region, subdomain: s.subdomain}))));
    } else {
      const key = {'cf-native-login': 'setup_cf_orgs', 'cf-orgs': 'setup_cf_orgs', 'cf-spaces': 'setup_cf_spaces', 'cf-instances': 'setup_cf_instances', 'cf-bindings': 'setup_cf_bindings'}[action];
      put(key, JSON.stringify(rows.map(r => ({guid: r.guid, name: r.name, instance_guid: r.relationships && r.relationships.service_instance && r.relationships.service_instance.data.guid}))));
    }
  }
  async function beforeBusiness() {
    if (!enabled(get('setup_enabled'))) return;
    guard();
    const oldBase = required('base_url');
    await ensureDestination();
    const current = String(insomnia.request.url);
    if (!current.startsWith(oldBase + '/') && current !== oldBase) throw new Error('URL fora da Destination ativa. Confira o Environment e a URL antes de enviar credenciais.');
    if (get('setup_api_path') && get('setup_api_path') !== '/odata/v2' && current.startsWith(oldBase + '/odata/v2/')) throw new Error('Os modelos existentes sao OData v2. Para outro servico, use Setup > Consultar entidade selecionada; nao converta o protocolo apenas trocando a URL.');
    insomnia.request.url = required('base_url') + current.slice(oldBase.length);
    applyAuth(get('destination_authorization'));
  }
  return {prepare, complete, beforeBusiness};
})();
