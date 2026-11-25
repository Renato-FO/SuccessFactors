# SuccessFactors — Insomnia API Library

Biblioteca **genérica** de chamadas SAP SuccessFactors OData v2 para Insomnia, com uma coleção essencial leve no Git Sync e o catálogo completo como importação opcional.

**Padrão: uma coleção essencial, com 50 chamadas e 7 entidades.** `User`, `Photo`, `EmpJob`, `FOCompany`, `FOLocation`, `AutoDelegateDetail` e `AutoDelegateConfig`. Inclui a pasta **Setup**, autenticação, identificação do usuário/gestor, subordinados, fotos, empresas, locais e delegações. As mesmas requisições atendem todos os clientes.

**Opcional em ZIP: 457 entidades padrão · 70 operações OData · 2.337 relacionamentos · 8.354 chamadas · 42 coleções.** O ZIP não é carregado como coleção pelo Git Sync.

Não contém URL real de API, partição, tenant, company ID, usuários, registros, credenciais ou extensões customizadas. Todos os valores são placeholders ou exemplos fictícios. Não é um SDK oficial SAP nem uma garantia de disponibilidade de todas as operações em qualquer tenant.

## Abrir pelo Git no Insomnia

1. Crie um projeto no Insomnia e selecione **Git Sync**.
2. Use a URL deste repositório, ou clone o repositório e selecione **Local folder**.
3. Selecione a branch `main`. Em `collections/` há somente `SuccessFactors-Essencial.yaml`.
4. Na coleção **SuccessFactors | Essencial**, crie e selecione um subambiente **privado** para o cliente.
5. Siga o **Setup nativo por cliente**, abaixo. O ambiente global com defaults é opcional quando o Environment privado já contém os valores necessários.

Alternativa: **Import → File** para importar apenas um arquivo YAML. O formato é o nativo **Insomnia v5**, validado contra o schema oficial 5.1. Não há exportação duplicada das mesmas coleções na raiz.

Git Sync e importação dependem da versão instalada do Insomnia. Consulte as [instruções oficiais de Git Sync](https://developer.konghq.com/how-to/synchronize-with-git/) e os [formatos de importação](https://developer.konghq.com/insomnia/import-export/).

## Importar somente as áreas desejadas

Baixe `optional/successfactors-complete.zip` e extraia **fora da pasta do projeto Git Sync**. No Insomnia, use **Import → File** e escolha apenas o YAML da área desejada. Por exemplo, `collections/02-Pessoas-e-Dados-Pessoais/Leitura-01.yaml`. Não é necessário importar o restante do ZIP. As pastas abaixo descrevem a organização dentro do arquivo opcional.

Se seu projeto antigo já carregou as 42 coleções e está lento ou bloqueado por alterações locais, crie um projeto novo com a versão atual. Isso evita depender de Pull/Discard no projeto antigo. Preserve seus ambientes privados e não descarte alterações locais para fazer essa migração. Também é possível importar apenas o YAML essencial e `environments/SuccessFactors.yaml` por arquivo em um projeto novo.

## Setup nativo por cliente

O Setup utiliza somente scripts nativos, executados pelos hooks da coleção. Não instala plugins, não duplica requisições por cliente e não abre aplicações auxiliares. Cada cliente/ambiente deve ter seu próprio **Environment privado**, criado manualmente no Insomnia. Selecione-o antes de executar as etapas. A configuração e os tokens são persistidos nesse Environment, sem limpar ou substituir outras variáveis.

### Caminho simples: service key do Destination Service

No Environment privado, preencha:

```json
{
  "setup_scope": "collection",
  "setup_private_environment": true,
  "base_url": "https://api.example.successfactors.com",
  "btp_token_url": "",
  "btp_client_id": "",
  "btp_client_secret": "",
  "destination_service_url": "",
  "destination_name": "",
  "page_size": "20",
  "skip": "0"
}
```

Use `url` da service key com `/oauth/token` em `btp_token_url`, `clientid` em `btp_client_id`, `clientsecret` em `btp_client_secret` e `uri` em `destination_service_url`. Alternativamente, adicione `destination_service_key` e cole o JSON da chave como objeto ou string JSON: o Setup aceita a chave direta ou o wrapper `credentials` e extrai esses quatro valores automaticamente. Não são montadas URLs trocando códigos de região: EU10, US10 e demais regiões usam os endpoints reais da chave.

Para os demais parâmetros das consultas (IDs, códigos e datas), use `environments/environment.example.json` como referência e preencha apenas os necessários no ambiente do cliente. O Setup não inventa IDs de pessoas ou empresas e não copia esses dados de outro Environment.

1. Execute **Setup → 01 — Conectar BTP e listar Destinations da subconta → Executar**. O token BTP é obtido automaticamente. As opções resumidas ficam em `setup_destinations_subaccount`.
2. Opcionalmente execute **02 — Listar Destinations da instancia**. As opções ficam em `setup_destinations_instance`.
3. Escolha uma opção e preencha seu nome em `destination_name`. Se as APIs de listagem retornarem 403, é possível informar um nome conhecido e tentar a resolução direta, conforme as permissões da credencial.
4. Execute **03 — Aplicar Destination selecionada**. O Setup resolve a Destination e grava `base_url`, `access_token`, `destination_authorization`, tipo de autenticação e validades. Quando a URL contém o sufixo `/odata/v2` ou `/odata/v4/...`, esse caminho é separado em `setup_api_path`.
5. Execute **04 — Consultar metadata e entidades** para descobrir EntitySets; os nomes ficam em `setup_entities`. Opcionalmente preencha `entity_name` e execute **Consultar entidade selecionada**.
6. Use as consultas existentes. Ao mudar de cliente, apenas selecione o Environment privado correspondente. A renovação ocorre antes da requisição quando o token expirou, está próximo de expirar, ou a Destination mudou.

Não há select dinâmico de serviços criado por scripts: o fluxo nativo apresenta listas nas respostas/variáveis e usa o nome ou GUID escolhido no Environment. Evite executar todas as etapas opcionais em lote: cada uma depende da configuração anterior. Destinations de instância prevalecem sobre Destinations de subconta com o mesmo nome na resolução padrão; o Setup não inventa uma precedência diferente.

### Descoberta opcional de Global Account e subcontas (CIS)

A chave do Destination Service **não** concede acesso às APIs de contas do BTP. Para executar as etapas **05–07**, forneça uma service key do **SAP Cloud Management Service (`cis`, plano `central`)**, configurada para `client_credentials`, em `cis_service_key`. O Setup lê `uaa.url`, `uaa.clientid`, `uaa.clientsecret` e `endpoints.accounts_service_url`. Também é possível preencher diretamente `cis_token_url`, `cis_client_id`, `cis_client_secret` e `cis_accounts_url`.

- **05** consulta `/accounts/v1/globalAccount` e guarda `setup_global_accounts` e `global_account_guid`.
- **06** consulta `/accounts/v1/subaccounts` e guarda as subcontas acessíveis em `setup_subaccounts`. Escolha `subaccount_guid`.
- **07** consulta a subconta selecionada e persiste `btp_region` e `subaccount_subdomain` quando retornados.

**Limite de escopo:** a API CIS consultada retorna a Global Account da credencial; não lista todas as Global Accounts de uma pessoa autenticada no cockpit. Para outra Global Account, use credenciais autorizadas para ela no Environment correspondente. As subcontas retornadas também são limitadas pelos escopos da credencial. Selecionar uma subconta não transforma a chave existente em uma chave dessa subconta e não concede permissões adicionais.

### Descoberta opcional da instância Destination (Cloud Foundry)

Para as etapas **08–14**, configure `cf_api_url` usando o API endpoint informado pelo BTP para a subconta/região. A etapa **08** consulta `/v3/info` e descobre os endpoints OAuth por `links.login.href`; não adivinha o host com base no nome da região.

A etapa **09** oferece **OAuth2 Authorization Code nativo** na aba **Auth**, com PKCE e navegador padrão. Exige um cliente OAuth registrado, redirect URI autorizado, fluxos suportados pelo UAA/IdP e os campos `cf_oauth_client_id`, `cf_oauth_client_secret` (se exigido), `cf_oauth_redirect_url`, `cf_authorization_url` e `cf_token_url`. Use o botão de obtenção de token do próprio Insomnia. O script tenta persistir `accessToken` exposto pelo SDK em `cf_access_token`; se a versão não expuser o token, indica explicitamente que ele deve ser copiado uma vez de Auth para o Environment privado. Alternativamente, forneça um token CF válido obtido por um fluxo autorizado fora da coleção.

**SSO não é iniciado pelo script.** A existência de login no cockpit não fornece automaticamente uma sessão CF, CIS ou Destination Service. Este fluxo não assume um cliente OAuth universal, não usa password grant e não coleta senha de usuário.

Depois de obter `cf_access_token`:

| Etapa | Escolha no Environment | Resultado |
|---|---|---|
| 10 — Listar organizações | `cf_org_guid` | `setup_cf_orgs` |
| 11 — Listar spaces | `cf_space_guid` | `setup_cf_spaces` |
| 12 — Descobrir instâncias Destination | `cf_instance_guid` | `setup_cf_instances` |
| 13 — Listar service keys existentes | `cf_binding_guid` | `setup_cf_bindings` |
| 14 — Importar service key selecionada | Nenhuma nova escolha | Preenche os quatro campos BTP/Destination |

A etapa **12** consulta offerings e planos do serviço `destination`, filtrando as instâncias pelo space selecionado. A etapa **14** exige que a key pertença à instância escolhida e que a sessão tenha permissão para ler credenciais. Não cria instâncias, service keys ou Destinations. Após a importação da key, execute **01** e **03**. Páginas CF são agregadas com limite de 100 e sem encaminhar o token para outro host.

### Tokens, persistência e limites

- O Setup guarda tokens e credenciais somente no escopo ativo escolhido por `setup_scope`: `collection` para o subambiente privado da coleção, ou `global` para um subambiente global privado explicitamente selecionado. Todos os campos de conexão devem estar nesse escopo; o runtime não busca credenciais ausentes em outro cliente/escopo.
- Os scripts nativos não expõem uma verificação confiável de `isPrivate`. `setup_private_environment=true` é uma declaração que você configura **depois de criar e selecionar o ambiente privado**. Não comprova nem torna privado um ambiente compartilhado. A configuração pública mantém essa opção desabilitada.
- A renovação BTP/CIS usa novamente `client_credentials`, pois esse fluxo não depende de refresh token. Tokens da Destination são obtidos novamente pelo serviço. Usa-se `expires_in` ou o `exp` do JWT, com antecedência de 60 segundos; sem validade conhecida, a resolução é repetida antes de enviar a consulta.
- O token CF de usuário depende do fluxo OAuth2 nativo e das políticas do IdP. Quando expirar, renove-o na etapa **09** ou substitua `cf_access_token`; a credencial Destination não renova sessões de usuário CF. O mesmo vale para `destination_user_token` em fluxos de propagação.
- A renovação acontece **antes** do envio. Não há repetição automática de uma operação após 401, evitando executar novamente escritas com efeito incerto. Confira permissões/revogação e execute **03** novamente se necessário.
- São aceitos headers `Bearer`, `Basic` e `NoAuthentication` retornados por Destinations Internet. mTLS, OnPremise, PrivateLink e fluxos que exigem certificados/proxies ou contexto adicional precisam de configuração própria; não são apresentados como resolvidos pelo Setup.
- `setup_api_path` permite consultar o metadata e uma entidade de outro serviço OData. Os modelos de negócio existentes continuam OData v2 e são bloqueados quando a Destination aponta para outro caminho/protocolo. O Setup não converte schemas, filtros ou paginação entre v2, v4 e REST.
- As respostas completas ficam no histórico local do Insomnia e podem conter credenciais. As listas persistidas pelo Setup são resumidas e não copiam senhas. Nenhum valor real é gerado ou versionado pelos scripts do repositório.

Referências: [scripts nativos e bibliotecas disponíveis](https://developer.konghq.com/insomnia/scripts/), [escopos de Environment e privados](https://developer.konghq.com/insomnia/environments/), [planos CIS](https://help.sap.com/docs/btp/sap-business-technology-platform/a508b724bf6d457ca7ac024b8e4b8457.html), [spec oficial SAP Accounts Service](https://github.com/SAP/crossplane-provider-btp/blob/main/internal/openapi_clients/btp-accounts-service-api-go/swagger.json), [Destination Service](https://help.sap.com/docs/connectivity/sap-btp-connectivity-cf/consuming-destination-service) e [Cloud Foundry v3](https://v3-apidocs.cloudfoundry.org/).

## Configuração e token — fluxo anterior

As chamadas de **00 — Autenticacao** foram preservadas para compatibilidade. Elas não habilitam o gerenciador de renovação do Setup. Para novas configurações por cliente, prefira o fluxo acima e não misture configurações entre escopos.

Todas as coleções usam o mesmo **ambiente global SuccessFactors**, definido em `environments/SuccessFactors.yaml`. Preencha a conexão uma única vez nesse ambiente, preferencialmente em um subambiente privado, e selecione-o nas coleções. Os ambientes locais das coleções guardam apenas chaves de registros e paginação. `environments/environment.example.json` serve como referência.

### Via SAP BTP Destination Service

Preencha:

| Variável | Valor a fornecer |
|---|---|
| `base_url` | URL do servidor de API SuccessFactors, sem `/odata/v2` |
| `btp_token_url` | `url` da service key do Destination Service, com `/oauth/token` |
| `btp_client_id` | `clientid` da service key |
| `btp_client_secret` | `clientsecret` da service key |
| `destination_service_url` | `uri` da service key, sem barra final |
| `destination_name` | Nome da Destination configurada para o SuccessFactors |

Execute **Conectar — BTP + SuccessFactors em uma chamada**. O script obtém o token BTP, consulta a Destination e salva automaticamente `btp_access_token` e `access_token` no ambiente global selecionado. O token fica disponível em todas as coleções que usam esse ambiente. Se expirar, execute **Conectar** novamente.

Também há chamadas separadas **01 — Token BTP** e **02 — Token SuccessFactors via Destination** para diagnóstico. A Destination deve estar configurada para entregar um token de acesso compatível com o SuccessFactors, por exemplo com OAuth2 SAML Bearer Assertion. O token BTP serve para consultar a Destination; o token retornado em `authTokens` é usado nas chamadas do SuccessFactors.

Se você preencher `base_url` em um subambiente da própria coleção, os scripts salvam os tokens nesse subambiente. Isso funciona para a coleção atual. Para compartilhar o token entre todas as coleções, mantenha a conexão no ambiente global **SuccessFactors** e selecione-o em cada coleção. Sem um ambiente global selecionado, o Insomnia não persiste variáveis gravadas apenas em `insomnia.globals`; por isso os scripts usam o ambiente da coleção como alternativa. A resposta principal de **Conectar** mostra o token BTP; o token do SuccessFactors é obtido pela segunda chamada do script e salvo em `access_token`.

### OAuth direto com SAML

Preencha `base_url`, `sf_company_id`, `sf_client_id` e `saml_assertion` no ambiente global. Execute **Alternativa — Token direto SAML**. O script salva `access_token` global automaticamente.

- `sf_company_id` é o ID do tenant, não o código de uma entidade legal.
- `sf_client_id` é a API Key de um cliente OAuth registrado.
- `saml_assertion` deve ser uma assertion SAML assinada, válida e codificada em Base64. Esta coleção faz a troca por token; não gera nem assina a assertion.

Também é possível preencher `access_token` manualmente. Veja [Requesting an Access Token](https://help.sap.com/docs/successfactors-platform/sap-successfactors-api-reference-guide-odata-v2/requesting-access-token?locale=en-US).

Use ambientes privados ou variáveis secretas do Insomnia para valores reais. Tokens e respostas salvos durante o uso são dados locais; revise os arquivos antes de sincronizar alterações com Git. O `.gitignore` protege arquivos auxiliares locais, mas não remove valores inseridos em coleções YAML já versionadas.

## Organização

| Pasta | Conteúdo |
|---|---|
| `00-Inicio` | Autenticação, metadata, catálogo, paginação e consultas parametrizadas |
| `01-Usuarios-e-Perfil` | Usuários, contas e fotos |
| `02-Pessoas-e-Dados-Pessoais` | Pessoas, documentos, contatos e dados globais |
| `03-Vinculos-e-Cargos` | Vínculos, dados de emprego e relações de trabalho |
| `04-Estrutura-Organizacional` | Empresas, locais, departamentos, divisões, posições e dados legais |
| `05-Cargos-e-Competencias` | Perfis de cargo, competências, habilidades e certificações |
| `06-Remuneracao-e-Folha` | Remuneração, pagamentos, deduções e folha |
| `07-Tempo-e-Ausencias` | Ponto, ausências, contas de tempo, escalas e feriados |
| `08-Beneficios` | Programas, inscrições, dependentes, planos e reembolsos |
| `09-Recrutamento` | Requisições, candidatos, candidaturas, entrevistas e ofertas |
| `10-Onboarding` | Processos e tarefas de onboarding |
| `11-Desempenho-e-Metas` | Formulários, metas, avaliações e calibração |
| `12-Talentos-e-Desenvolvimento` | Mentoria, aprendizagem, sucessão e talentos |
| `13-Workflows` | Solicitações, etapas e aprovações |
| `14-Permissoes-e-Grupos` | Grupos e permissões |
| `15-Listas-e-Localizacao` | Picklists, países, moedas e idiomas |
| `16-Plataforma-e-Documentos` | Documentos, anexos e serviços da plataforma |
| `17-Operacoes` | Function imports, incluindo operações com efeitos de escrita |

No ZIP opcional, coleções grandes são divididas em partes de até 35 entidades. Em cada área, **Leitura** e **Escrita** são coleções separadas. Pastas de entidades contêm uma subpasta **Relacionamentos** com navegação por chave e consultas com `$expand`. A coleção essencial não carrega esse conjunto extenso de relacionamentos.

## Usar as consultas

1. Execute **Listar** na entidade desejada. O tamanho padrão de página é 20.
2. Quando há resultado, o script monta a chave OData do primeiro registro e salva `key_NomeDaEntidade`. Isso permite executar **Buscar por chave** e as navegações.
3. Em **Filtrar**, substitua `REPLACE_ME` e datas/números fictícios. Campos `$select` são exemplos editáveis.
4. Nas consultas temporais, ajuste `as_of_date`, `from_date` e `to_date`.
5. `d.__next`, quando presente, é salvo em `next_page_url`. Use **Proxima pagina** na mesma coleção, ou copie o valor para o ambiente de diagnóstico. Preserve a URL fornecida pelo servidor e confira seu host.

As consultas **Contar** usam `/$count`; o suporte varia por entidade. Expansões retornam no máximo um registro principal por padrão, mas podem trazer múltiplos registros relacionados. As chamadas de foto consultam a entidade OData; a interpretação de conteúdo binário/Base64 depende do retorno da API.

Os exemplos não pressupõem IDs existentes. Datas fictícias precisam ser alteradas para refletir o período que deseja consultar. Uma consulta vazia não comprova ausência de cadastro: datas efetivas, permissões e filtros influenciam o resultado.

## Modelos de escrita e operações

Quando a assinatura de referência indica suporte, as coleções de escrita incluem **POST**, **MERGE**, **upsert** e **DELETE**. Os corpos são pontos de partida com campos técnicos e valores fictícios; revise campos obrigatórios, regras, chaves e formatos na documentação/metadata do seu ambiente. `MERGE` atualiza propriedades de um registro; `upsert` usa o endpoint OData `/upsert`.

As 70 operações têm método e parâmetros derivados das assinaturas OData. Algumas, inclusive operações chamadas por GET, podem produzir efeitos no serviço. Os modelos não foram executados contra um tenant para validar regras de negócio. Não execute uma coleção inteira de escrita ou de operações como se fosse um teste de leitura.

## Catálogo e geração

- `catalog/entities.csv`: índice de entidades e operações.
- `catalog/entities.json`: campos técnicos, tipos, chaves e relacionamentos.
- `catalog/functions.json`: assinaturas das operações.
- `catalog/summary.json`: contagem e arquivos das coleções.
- `catalog/lite-summary.json`: contagem e entidades da coleção essencial ativa.
- `scripts/setup_collection.py`: estrutura da pasta Setup e configuração pública sem credenciais.
- `scripts/insomnia/setup-runtime.js`: fonte única dos hooks nativos, embutida no YAML durante a geração.
- `optional/successfactors-complete.zip`: arquivos completos, disponíveis para importação seletiva.
- `schemas/insomnia.schema.5.1.json`: schema público oficial do Insomnia, preservado com seu identificador de origem.

A biblioteca cobre um subconjunto amplo de entidades padrão. O SuccessFactors expõe superfícies diferentes conforme módulos, versão, permissões e configuração. Não inclui extensões `cust_*`, entidades de templates numerados ou campos customizados. Nomes de países e versões presentes em tipos padrão são parte das assinaturas públicas, não identificadores de um tenant.

Para gerar novamente, forneça um metadata local, que não deve ser publicado:

```sh
python -m pip install -r requirements.txt
python scripts/generate.py --metadata .local/metadata.xml --out .
python scripts/validate.py
node scripts/test-scripts.mjs
npm ci --ignore-scripts
npm test
```

O gerador usa uma lista de famílias padrão, ignora labels, defaults, URLs e valores de registros, e não copia o XML de origem. Ao terminar, empacota as coleções completas no ZIP e mantém apenas a essencial em `collections/`. O script `package_collections.py` também permite reconstruir a essencial a partir do ZIP existente. A geração não modifica a API.

## Validação

O validador verifica o schema oficial v5.1, IDs únicos, referências de variáveis, contagens, configuração sem credenciais, ausência de aliases YAML e sincronismo entre a fonte do runtime e os hooks gerados. Os testes Node verificam a sintaxe dos scripts, o encadeamento OAuth com respostas simuladas, persistência no escopo ativo, renovação/expiração, troca de clientes, paginação, descoberta e montagem de chaves OData. Não enviam requisições reais. A mesma validação roda no GitHub Actions. Isso valida os artefatos; a disponibilidade de cada chamada continua dependendo da API e das permissões configuradas no seu tenant.
