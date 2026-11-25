# SuccessFactors — Insomnia API Library

Biblioteca **genérica** de chamadas SAP SuccessFactors OData v2 para Insomnia, com uma coleção essencial leve no Git Sync e o catálogo completo como importação opcional.

**Padrão: uma coleção essencial, com 7 entidades.** `User`, `Photo`, `EmpJob`, `FOCompany`, `FOLocation`, `AutoDelegateDetail` e `AutoDelegateConfig`. Inclui autenticação, identificação do usuário/gestor, subordinados, fotos, empresas, locais e delegações.

**Opcional em ZIP: 457 entidades padrão · 70 operações OData · 2.337 relacionamentos · 8.354 chamadas · 42 coleções.** O ZIP não é carregado como coleção pelo Git Sync.

Não contém URL real de API, partição, tenant, company ID, usuários, registros, credenciais ou extensões customizadas. Todos os valores são placeholders ou exemplos fictícios. Não é um SDK oficial SAP nem uma garantia de disponibilidade de todas as operações em qualquer tenant.

## Abrir pelo Git no Insomnia

1. Crie um projeto no Insomnia e selecione **Git Sync**.
2. Use a URL deste repositório, ou clone o repositório e selecione **Local folder**.
3. Selecione a branch `main`. Em `collections/` há somente `SuccessFactors-Essencial.yaml`.
4. Abra **Environments → SuccessFactors** e crie um subambiente **privado** para preencher seus valores reais.
5. Selecione esse ambiente global na coleção **SuccessFactors | Essencial**.

Alternativa: **Import → File** para importar apenas um arquivo YAML. O formato é o nativo **Insomnia v5**, validado contra o schema oficial 5.1. Não há exportação duplicada das mesmas coleções na raiz.

Git Sync e importação dependem da versão instalada do Insomnia. Consulte as [instruções oficiais de Git Sync](https://developer.konghq.com/how-to/synchronize-with-git/) e os [formatos de importação](https://developer.konghq.com/insomnia/import-export/).

## Importar somente as áreas desejadas

Baixe `optional/successfactors-complete.zip` e extraia **fora da pasta do projeto Git Sync**. No Insomnia, use **Import → File** e escolha apenas o YAML da área desejada. Por exemplo, `collections/02-Pessoas-e-Dados-Pessoais/Leitura-01.yaml`. Não é necessário importar o restante do ZIP. As pastas abaixo descrevem a organização dentro do arquivo opcional.

Se seu projeto antigo já carregou as 42 coleções e está lento ou bloqueado por alterações locais, crie um projeto novo com a versão atual. Isso evita depender de Pull/Discard no projeto antigo. Preserve seus ambientes privados e não descarte alterações locais para fazer essa migração. Também é possível importar apenas o YAML essencial e `environments/SuccessFactors.yaml` por arquivo em um projeto novo.

## Configuração e token

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
- `optional/successfactors-complete.zip`: arquivos completos, disponíveis para importação seletiva.
- `schemas/insomnia.schema.5.1.json`: schema público oficial do Insomnia, preservado com seu identificador de origem.

A biblioteca cobre um subconjunto amplo de entidades padrão. O SuccessFactors expõe superfícies diferentes conforme módulos, versão, permissões e configuração. Não inclui extensões `cust_*`, entidades de templates numerados ou campos customizados. Nomes de países e versões presentes em tipos padrão são parte das assinaturas públicas, não identificadores de um tenant.

Para gerar novamente, forneça um metadata local, que não deve ser publicado:

```sh
python -m pip install -r requirements.txt
python scripts/generate.py --metadata .local/metadata.xml --out .
python scripts/validate.py
node scripts/test-scripts.mjs
```

O gerador usa uma lista de famílias padrão, ignora labels, defaults, URLs e valores de registros, e não copia o XML de origem. Ao terminar, empacota as coleções completas no ZIP e mantém apenas a essencial em `collections/`. O script `package_collections.py` também permite reconstruir a essencial a partir do ZIP existente. A geração não modifica a API.

## Validação

O validador verifica o schema oficial v5.1, IDs únicos, referências de variáveis, contagens, configuração sem credenciais e marcadores específicos de ambiente. Os testes Node verificam a sintaxe dos scripts, o encadeamento OAuth com respostas simuladas, o armazenamento global dos tokens e a montagem de chaves OData. Não enviam requisições reais. A mesma validação roda no GitHub Actions. Isso valida os artefatos; a disponibilidade de cada chamada continua dependendo da API e das permissões configuradas no seu tenant.
