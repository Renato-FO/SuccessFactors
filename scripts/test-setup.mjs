import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
import test from 'node:test';

const require=createRequire(import.meta.url);
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
const source=fs.readFileSync(new URL('./insomnia/setup-runtime.js',import.meta.url),'utf8');
const defaults={setup_private_environment:true,setup_scope:'collection',
  btp_token_url:'https://auth.example.com/oauth/token',btp_client_id:'example-client',btp_client_secret:'example-secret',
  destination_service_url:'https://destination.example.com',destination_name:'EXAMPLE',base_url:'https://api.example.com'};
const destination=(options={})=>({destinationConfiguration:{URL:'https://api.example.com/odata/v2',Authentication:'OAuth2ClientCredentials',ProxyType:'Internet',...options},authTokens:[{type:'Bearer',value:'example-sf-token',expires_in:'3600'}]});
function mock(initial={},route=()=>{throw new Error('Unexpected network request');},globalScope=false){
  const values=new Map(Object.entries({...defaults,...initial}));
  const other=new Map([['unrelated','preserve-me']]);
  const sent=[];const writes=[];const headers=new Map();
  let response={code:200,json:()=>({}),text:()=>''};
  const wrap=map=>({get:k=>map.get(k),set:(k,v)=>{map.set(k,v);writes.push([map===values?'active':'other',k]);}});
  const insomnia={environment:wrap(globalScope?other:values),globals:wrap(globalScope?values:other),
    variables:{get:k=>values.get(k)},
    request:{url:'https://api.example.com/odata/v2/User',method:'GET',
      auth:{update:(options,type)=>{assert.deepEqual(options,[]);assert.equal(type,'noauth');},toJSON:()=>({oauth2:[]})},
      addHeader:({key,value})=>headers.set(key,value),removeHeader:key=>headers.delete(key)},
    get response(){return response;},
    sendRequest:(request,callback)=>{
      sent.push(request);
      try{
        const result=route(request,sent.length);
        callback(null,{code:result.code??200,json:()=>result.body??result});
      }catch(error){callback(error);}
    }};
  return {values,other,sent,writes,headers,insomnia,
    response:(body,code=200)=>{response={code,json:()=>body,text:()=>typeof body==='string'?body:JSON.stringify(body)};},
    api:()=>new AsyncFunction('insomnia','require',source+'\nreturn SFSetup;')(insomnia,require)};
}
function cached(ctx){
  ctx.values.set('btp_access_token','example-btp-token');
  ctx.values.set('btp_token_expires_at',Date.now()+3600000);
  ctx.values.set('btp_token_context',JSON.stringify([ctx.values.get('btp_token_url'),ctx.values.get('btp_client_id')]));
}
async function select(ctx){ctx.response(destination());await (await ctx.api()).complete('destination');}

test('requires private-environment configuration before network or writes',async()=>{
  const ctx=mock({setup_private_environment:false});
  await assert.rejects((await ctx.api()).prepare('destinations-subaccount'),/PRIVADO/);
  assert.equal(ctx.sent.length,0);assert.equal(ctx.writes.length,0);
});
test('imports region-independent service keys and stores only in the active scope',async()=>{
  for(const scope of ['collection','global']){
    const ctx=mock({setup_scope:scope,destination_service_key:JSON.stringify({credentials:{url:'https://auth.eu.example.com',uri:'https://dest.eu.example.com',clientid:'generic-client',clientsecret:'generic-secret'}})},request=>{
      assert.equal(request.url,'https://auth.eu.example.com/oauth/token');
      assert.equal(request.auth.type,'basic');
      assert.equal(request.body.urlencoded[0].value,'client_credentials');
      return {access_token:'example-btp-token',expires_in:3600};
    },scope==='global');
    await (await ctx.api()).prepare('destinations-subaccount');
    assert.equal(ctx.insomnia.request.url,'https://dest.eu.example.com/destination-configuration/v1/subaccountDestinations');
    assert.equal(ctx.values.get('btp_access_token'),'example-btp-token');
    assert.ok(ctx.writes.every(([scope])=>scope==='active'));
    assert.equal(ctx.other.get('unrelated'),'preserve-me');
  }
});
test('destination lists cache display fields only, even when the API returns passwords',async()=>{
  const ctx=mock();cached(ctx);
  ctx.response([{Name:'EXAMPLE',URL:'https://api.example.com',Authentication:'BasicAuthentication',Password:'do-not-cache',User:'do-not-cache'}]);
  await (await ctx.api()).complete('destinations-subaccount');
  const saved=ctx.values.get('setup_destinations_subaccount');
  assert.equal(JSON.parse(saved)[0].name,'EXAMPLE');assert.ok(!saved.includes('do-not-cache'));
});
test('applying a Destination fills URL and token without overwriting unrelated configuration',async()=>{
  const ctx=mock({custom_setting:'keep'});await select(ctx);
  assert.equal(ctx.values.get('base_url'),'https://api.example.com');
  assert.equal(ctx.values.get('access_token'),'example-sf-token');
  assert.equal(ctx.values.get('setup_enabled'),true);
  assert.equal(ctx.values.get('custom_setting'),'keep');
});
test('fresh tokens are reused and expiry refreshes before a business request',async()=>{
  const ctx=mock({},request=>{
    if(request.method==='POST')return {access_token:'renewed-btp-token',expires_in:3600};
    assert.equal(request.header.Authorization,'Bearer renewed-btp-token');
    return {...destination(),authTokens:[{type:'Bearer',value:'renewed-sf-token',expires_in:3600}]};
  });cached(ctx);await select(ctx);
  await (await ctx.api()).beforeBusiness();assert.equal(ctx.sent.length,0);
  assert.equal(ctx.headers.get('Authorization'),'Bearer example-sf-token');
  ctx.values.set('destination_expires_at',Date.now());ctx.values.set('btp_token_expires_at',Date.now());
  await (await ctx.api()).beforeBusiness();
  assert.equal(ctx.sent.length,2);assert.equal(ctx.headers.get('Authorization'),'Bearer renewed-sf-token');
  assert.equal(ctx.insomnia.request.url,'https://api.example.com/odata/v2/User');
});
test('changing clients or Destinations does not reuse a token from another context',async()=>{
  const one=mock();const two=mock({destination_name:'OTHER'});cached(one);cached(two);
  await select(one);await select(two);
  two.values.set('destination_name','CHANGED');
  const ctx=mock(Object.fromEntries(two.values),request=>{
    assert.ok(request.url.endsWith('/CHANGED'));return destination();
  });
  await (await ctx.api()).beforeBusiness();assert.equal(ctx.sent.length,1);
  assert.equal(one.values.get('destination_name'),'EXAMPLE');
});
test('expired opaque tokens without TTL are refreshed rather than assumed valid',async()=>{
  const ctx=mock({},()=>destination());cached(ctx);ctx.response({...destination(),authTokens:[{type:'Bearer',value:'opaque-no-ttl'}]});
  await (await ctx.api()).complete('destination');
  assert.equal(ctx.values.get('destination_expires_at'),0);
  await (await ctx.api()).beforeBusiness();assert.equal(ctx.sent.length,1);
});
test('Basic and NoAuthentication destinations use the proper outgoing auth',async()=>{
  const basic=mock();basic.response({...destination({Authentication:'BasicAuthentication'}),authTokens:[{http_header:{key:'Authorization',value:'Basic ZXhhbXBsZTpleGFtcGxl'},expires_in:3600}]});
  await (await basic.api()).complete('destination');await (await basic.api()).beforeBusiness();
  assert.equal(basic.headers.get('Authorization'),'Basic ZXhhbXBsZTpleGFtcGxl');
  const none=mock();none.response(destination({Authentication:'NoAuthentication'}));
  await (await none.api()).complete('destination');await (await none.api()).beforeBusiness();
  assert.equal(none.headers.has('Authorization'),false);
});
test('failed resolution and unsupported proxy preserve the previous environment',async()=>{
  const ctx=mock({access_token:'old-token',base_url:'https://previous.example.com'});
  ctx.response(destination({ProxyType:'OnPremise'}));
  await assert.rejects((await ctx.api()).complete('destination'),/OnPremise/);
  assert.equal(ctx.values.get('base_url'),'https://previous.example.com');assert.equal(ctx.values.get('access_token'),'old-token');
  ctx.response({},403);await assert.rejects((await ctx.api()).complete('destination'),/escopos/);
});
test('CIS discovery remains scoped to its credential and records returned region',async()=>{
  const ctx=mock({cis_service_key:JSON.stringify({endpoints:{accounts_service_url:'https://accounts.example.com'},uaa:{url:'https://cis-auth.example.com',clientid:'example-cis',clientsecret:'example-secret'}})},()=>({access_token:'example-cis-token',expires_in:3600}));
  const api=await ctx.api();await api.prepare('cis-global');
  assert.equal(ctx.insomnia.request.url,'https://accounts.example.com/accounts/v1/globalAccount');
  ctx.response({guid:'example-global',displayName:'Example'});await api.complete('cis-global');
  ctx.values.set('subaccount_guid','example-subaccount');await api.prepare('cis-subaccount');
  ctx.response({guid:'example-subaccount',region:'us10',subdomain:'example'});await api.complete('cis-subaccount');
  assert.equal(ctx.values.get('btp_region'),'us10');
  assert.equal(ctx.values.get('btp_token_url'),defaults.btp_token_url);
});
test('CF instances are filtered to Destination plans and the selected space',async()=>{
  const ctx=mock({cf_api_url:'https://cf.example.com',cf_access_token:'example-cf-token',cf_space_guid:'example-space'},request=>{
    if(request.url.includes('service_offerings'))return {resources:[{guid:'example-offering'}]};
    assert.ok(request.url.includes('service_offering_guids=example-offering'));return {resources:[{guid:'example-plan'}]};
  });
  await (await ctx.api()).prepare('cf-instances');
  assert.equal(ctx.insomnia.request.url,'https://cf.example.com/v3/service_instances?space_guids=example-space&service_plan_guids=example-plan');
});
test('CF pages stay on the same host and only selected existing keys are imported',async()=>{
  const ctx=mock({cf_api_url:'https://cf.example.com',cf_access_token:'example-cf-token',cf_instance_guid:'example-instance',cf_binding_guid:'example-key'});
  ctx.response({resources:[],pagination:{next:{href:'https://untrusted.example.com/steal'}}});
  await assert.rejects((await ctx.api()).complete('cf-bindings'),/fora do host/);assert.equal(ctx.sent.length,0);
  await assert.rejects((await ctx.api()).prepare('cf-key'),/Liste e selecione/);
  ctx.values.set('setup_cf_bindings',JSON.stringify([{guid:'example-key',instance_guid:'example-instance'}]));
  await (await ctx.api()).prepare('cf-key');
  assert.ok(ctx.insomnia.request.url.endsWith('/example-key/details'));
  ctx.response({credentials:{url:'https://new-auth.example.com',uri:'https://new-dest.example.com',clientid:'example-new',clientsecret:'example-new-secret'}});
  await (await ctx.api()).complete('cf-key');
  assert.equal(ctx.values.get('destination_service_url'),'https://new-dest.example.com');
  assert.equal(ctx.values.get('setup_enabled'),false);
});
test('native OAuth falls back explicitly when the scripting SDK cannot expose a user token',async()=>{
  const ctx=mock();ctx.response({resources:[]});
  await assert.rejects((await ctx.api()).complete('cf-native-login'),/cf_access_token/);
});
test('metadata discovery handles real namespaced XML without storing employee data',async()=>{
  const ctx=mock();ctx.response('<?xml version="1.0"?><edmx:Edmx xmlns:edmx="urn:edmx"><edmx:DataServices><Schema xmlns="urn:edm"><EntityContainer Name="Container"><EntitySet Name="User" EntityType="Example.User"/><EntitySet Name="EmpJob" EntityType="Example.EmpJob"/></EntityContainer></Schema></edmx:DataServices></edmx:Edmx>');
  await (await ctx.api()).complete('metadata');
  assert.deepEqual(JSON.parse(ctx.values.get('setup_entities')),['EmpJob','User']);
});
test('a configured v4 service supports generic entity queries while v2 models stay protected',async()=>{
  const ctx=mock({entity_name:'User',page_size:'5'});
  ctx.response(destination({URL:'https://api.example.com/odata/v4/service'}));await (await ctx.api()).complete('destination');
  await (await ctx.api()).prepare('entity');
  assert.equal(ctx.insomnia.request.url,'https://api.example.com/odata/v4/service/User?$top=5');
  ctx.insomnia.request.url='https://api.example.com/odata/v2/User';
  await assert.rejects((await ctx.api()).beforeBusiness(),/modelos existentes/);
});
test('refresh does not inject a credential into a URL outside the active Destination',async()=>{
  const ctx=mock();await select(ctx);ctx.insomnia.request.url='https://untrusted.example.com/User';
  await assert.rejects((await ctx.api()).beforeBusiness(),/fora da Destination/);
  assert.equal(ctx.headers.has('Authorization'),false);
});
test('tokens already expired in a service response are not installed',async()=>{
  const claims=Buffer.from(JSON.stringify({exp:1})).toString('base64url');
  const ctx=mock({access_token:'keep-existing'});
  ctx.response({...destination(),authTokens:[{type:'Bearer',value:'header.'+claims+'.signature'}]});
  await assert.rejects((await ctx.api()).complete('destination'),/token expirado/);
  assert.equal(ctx.values.get('access_token'),'keep-existing');
});
