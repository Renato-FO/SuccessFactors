import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = JSON.parse(fs.readFileSync(new URL('../.local/script-fixtures.json', import.meta.url), 'utf8'));
const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
for (const code of source.scripts) new AsyncFunction('insomnia', code);

function context(json, destinationJson = {authTokens:[{value:'mock-sf-token'}]}, collectionScope = false) {
  const global = new Map([
    ['destination_service_url','https://destination.example.com/'],
    ['destination_name','EXAMPLE_DESTINATION']
  ]);
  const local = new Map();
  if (collectionScope) local.set('base_url','https://api.example.successfactors.com');
  else global.set('base_url','https://api.example.successfactors.com');
  let sent = 0;
  const chain = {
    get to(){return this;},get be(){return this;},get and(){return this;},get not(){return this;},
    get empty(){return this;},a(type){assert.equal(type,'string');return this;},
    eql(value){assert.equal(value,200);return this;}
  };
  return {
    global,local,get sent(){return sent;},
    insomnia:{
      response:{code:200,json:()=>json},
      globals:{set:(k,v)=>global.set(k,v),get:k=>global.get(k)},
      baseGlobals:{get:()=>undefined},
      baseEnvironment:{get:()=>undefined},
      environment:{set:(k,v)=>local.set(k,v),get:k=>local.get(k)},
      variables:{get:k=>local.get(k)??global.get(k)},
      test:(_name,fn)=>fn(),expect:()=>chain,
      sendRequest:(request,callback)=>{
        sent++;
        assert.equal(request.url,'https://destination.example.com/destination-configuration/v1/destinations/EXAMPLE_DESTINATION');
        assert.equal(request.method,'GET');
        assert.equal(request.header.Authorization,'Bearer mock-btp-token');
        callback(null,{code:200,json:()=>destinationJson});
      }
    }
  };
}
async function run(name,ctx){await new AsyncFunction('insomnia',source.fixtures[name])(ctx.insomnia);}

const connect=context({access_token:'mock-btp-token'});
await run('connect',connect);
assert.equal(connect.global.get('btp_access_token'),'mock-btp-token');
assert.equal(connect.global.get('access_token'),'mock-sf-token');
assert.equal(connect.local.size,0);
assert.equal(connect.sent,1);
const collectionConnect=context({access_token:'mock-btp-token'},undefined,true);
await run('connect',collectionConnect);
assert.equal(collectionConnect.local.get('access_token'),'mock-sf-token');
assert.equal(collectionConnect.local.get('btp_access_token'),'mock-btp-token');
assert.equal(collectionConnect.global.has('access_token'),false);
await assert.rejects(run('connect',context({})),/Token BTP ausente/);
await assert.rejects(run('connect',context({access_token:'mock-btp-token'},{authTokens:[{error:'mock error'}]})),/token utilizável/);
for (const name of ['btp','saml']){
  const ctx=context({access_token:'mock-token'});
  await run(name,ctx);
  assert.equal(ctx.global.get(name==='btp'?'btp_access_token':'access_token'),'mock-token');
  assert.equal(ctx.local.size,0);
}
const company=context({d:{results:[{externalCode:"EXAMPLE'CODE",startDate:'/Date(946684800000)/'}],__next:'https://api.example.successfactors.com/odata/v2/FOCompany?$skiptoken=EXAMPLE'}});
await run('company_key',company);
assert.equal(company.local.get('key_FOCompany'),"externalCode='EXAMPLE''CODE',startDate=datetime'2000-01-01T00:00:00'");
assert.ok(company.local.get('next_page_url').endsWith('$skiptoken=EXAMPLE'));
const user=context({d:{results:[{userId:'USER_ID'}]}});
await run('user_key',user);
assert.equal(user.local.get('key_User'),"userId='USER_ID'");
console.log(`OK: ${source.scripts.length} unique scripts compile; mocked OAuth chain, shared token storage, failure paths, key escaping, dates and pagination passed.`);
