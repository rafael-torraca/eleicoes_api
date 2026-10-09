# Eleições API

API desenvolvida em Python com FastAPI para consultar resultados eleitorais disponibilizados pelo Tribunal Superior Eleitoral (TSE).

O projeto foi estruturado de forma modular para permitir futuras integrações com Telegram, WhatsApp, Discord e um site, sem duplicar as regras de negócio.

## Tecnologias

- Python 3.11 ou superior
- FastAPI
- Uvicorn
- HTTPX
- Pydantic Settings
- Pytest
- Ruff

## Funcionalidades atuais

- Consultar candidatos à Presidência e suas votações.
- Consultar resultados nacionais ou por unidade federativa (UF).
- Consultar a votação de um candidato por estado.
- Retornar o total nacional oficial informado pelo TSE.
- Selecionar o turno da eleição por parâmetro.
- Identificar códigos de eleição pela configuração do TSE.
- Armazenar respostas HTTP em cache temporário.
- Registrar requisições, tempos de resposta e falhas em logs JSON.
- Padronizar respostas de erro da API.
- Executar testes automatizados sem depender do TSE.

## Arquitetura do projeto

```text
eleicoes_api/
├── src/
│   └── eleicoes_api/
│       ├── api/
│       │   ├── routes/
│       │   │   ├── elections.py
│       │   │   └── health.py
│       │   ├── dependencies.py
│       │   ├── exception_handlers.py
│       │   └── middleware.py
│       ├── application/
│       │   └── election_service.py
│       ├── core/
│       │   ├── config.py
│       │   └── logging_config.py
│       ├── domain/
│       │   ├── errors.py
│       │   ├── repositories.py
│       │   └── schemas.py
│       ├── infrastructure/
│       │   └── tse/
│       │       ├── client.py
│       │       └── repository.py
│       └── main.py
├── clients/
├── tests/
├── .env
├── .env.example
├── pyproject.toml
└── README.md
```

### Responsabilidades

| Módulo | Responsabilidade |
|---|---|
| `api/` | Endpoints HTTP, dependências, middleware e tratamento de erros. |
| `application/` | Coordenação das consultas e validação das regras de aplicação. |
| `core/` | Configurações e logging. |
| `domain/` | Modelos de dados, contratos e exceções do domínio eleitoral. |
| `infrastructure/tse/` | Requisições HTTP, cache e interpretação dos arquivos do TSE. |
| `clients/` | Espaço reservado para futuros clientes, como Telegram e Discord. |
| `tests/` | Testes automatizados das diferentes camadas. |

## Requisitos

Instale o Python 3.11 ou superior e utilize um terminal PowerShell na raiz do projeto.

### 1. Criar o ambiente virtual

```powershell
python -m venv .venv
```

### 2. Ativar o ambiente virtual

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar o projeto e as dependências

```powershell
python -m pip install -e ".[dev]"
```

O modo editável permite modificar o código em `src/` sem reinstalar o projeto a cada alteração.

## Configuração

Crie o arquivo `.env` na raiz do projeto. Você pode utilizar `.env.example` como referência.

```dotenv
APP_NAME=Eleições API
APP_VERSION=0.1.0
APP_DESCRIPTION=API para consulta de dados eleitorais do TSE.
ENVIRONMENT=development

DEFAULT_ELECTION_YEAR=2026

TSE_HTTP_TIMEOUT=15
TSE_CACHE_TTL=15
TSE_CACHE_MAX_ENTRIES=512
```

| Variável | Descrição | Padrão |
|---|---|---|
| `APP_NAME` | Nome da API. | `Eleições API` |
| `APP_VERSION` | Versão da aplicação. | `0.1.0` |
| `ENVIRONMENT` | Ambiente de execução. | `development` |
| `DEFAULT_ELECTION_YEAR` | Ano utilizado quando não informado. | `2026` |
| `TSE_HTTP_TIMEOUT` | Timeout HTTP em segundos. | `15` |
| `TSE_CACHE_TTL` | Validade das respostas armazenadas em cache, em segundos. | `15` |
| `TSE_CACHE_MAX_ENTRIES` | Quantidade máxima de entradas no cache HTTP. | `512` |

Definir `TSE_CACHE_TTL=0` desativa o armazenamento de novas respostas em cache.

**Importante:** não versione o arquivo `.env` caso ele contenha credenciais ou outros dados secretos.

## Executar a API

Na raiz do projeto, execute:

```powershell
uvicorn eleicoes_api.main:app --app-dir src --reload
```

Por padrão, a API estará disponível em:

- API local: http://127.0.0.1:8000
- Documentação interativa: http://127.0.0.1:8000/docs
- Esquema OpenAPI: http://127.0.0.1:8000/openapi.json
- Verificação de saúde: http://127.0.0.1:8000/health

A opção `--reload` reinicia o servidor quando o código muda. Utilize-a durante o desenvolvimento, não como estratégia de execução em produção.

## Endpoints disponíveis

### Verificar se a API está funcionando

```http
GET /health
```

Resposta esperada:

```json
{
  "status": "ok"
}
```

### Consultar os resultados de um cargo

```http
GET /v1/eleicoes/cargos/{office}/resultados
```

Parâmetros:

| Parâmetro | Obrigatório | Descrição |
|---|---|---|
| `office` | Sim | Cargo eleitoral, como `presidente`. |
| `ano` | Não | Ano da eleição. Padrão: `2026`. |
| `uf` | Não | Sigla da unidade federativa, como `MG`. |
| `turno` | Não | Turno da eleição: `1` ou `2`. Padrão: `1`. |

Exemplos:

Resultados nacionais da Presidência:

```http
GET /v1/eleicoes/cargos/presidente/resultados
```

Resultados presidenciais em Minas Gerais:

```http
GET /v1/eleicoes/cargos/presidente/resultados?uf=MG
```

Resultados presidenciais em São Paulo:

```http
GET /v1/eleicoes/cargos/presidente/resultados?uf=SP
```

Resultados de um ano específico:

```http
GET /v1/eleicoes/cargos/presidente/resultados?ano=2026&uf=MG&turno=1
```

### Consultar os votos de um candidato por UF

```http
GET /v1/eleicoes/cargos/{office}/votos-por-uf
```

Parâmetros:

| Parâmetro | Obrigatório | Descrição |
|---|---|---|
| `office` | Sim | Cargo eleitoral; inicialmente, `presidente`. |
| `candidato` | Sim | Nome ou número do candidato. |
| `ano` | Não | Ano da eleição. Padrão: `2026`. |
| `turno` | Não | Turno da eleição. Padrão: `1`. |

Exemplo:

```http
GET /v1/eleicoes/cargos/presidente/votos-por-uf?candidato=22&turno=1
```

Esse endpoint retorna a identificação do candidato, seu partido, o total nacional oficial e os votos distribuídos pelas UFs.

Formato ilustrativo:

```json
{
  "year": 2026,
  "office": "presidente",
  "turn": 1,
  "candidate_number": 22,
  "candidate_name": "NOME DO CANDIDATO",
  "party": "PL",
  "total_votes": 1000000,
  "votes_by_state": {
    "MG": 150000,
    "SP": 300000
  }
}
```

Os valores acima são fictícios e servem apenas para demonstrar o formato.

**Observação sobre o total:** a API utiliza o total da consulta nacional do TSE. Ela não substitui esse valor pela soma das UFs, pois o resultado nacional pode incluir votos no exterior ou outras diferenças de abrangência.

## Integração com o TSE

O cliente HTTP está em:

```text
src/eleicoes_api/infrastructure/tse/client.py
```

Ele é responsável por:

- Realizar requisições HTTP assíncronas.
- Aplicar timeout.
- Validar respostas HTTP e JSON.
- Armazenar temporariamente respostas em cache.
- Registrar eventos de sucesso, falhas e cache nos logs.

O repositório eleitoral está em:

```text
src/eleicoes_api/infrastructure/tse/repository.py
```

Ele é responsável por:

- Consultar a configuração oficial das eleições.
- Resolver os códigos do cargo, da eleição e do turno.
- Montar as URLs dos resultados.
- Interpretar os arquivos JSON.
- Converter os registros para os modelos internos.
- Organizar os candidatos por quantidade de votos.
- Consultar a votação por UF.

A configuração eleitoral utilizada para identificar os códigos é disponibilizada pelo TSE em:

http://resultados.tse.jus.br/oficial/comum/config/ele-c.json

A integração deve sempre ser validada contra a configuração e os arquivos oficiais disponíveis para a eleição consultada.

## Cache e desempenho

O cache HTTP é mantido em memória no `TSEClient`.

Por padrão:

- As respostas ficam armazenadas por 15 segundos.
- São permitidas até 512 entradas.
- Respostas expiradas deixam de ser utilizadas.
- Falhas HTTP não são armazenadas como respostas válidas.

A consulta dos votos de um candidato utiliza o resultado nacional e consulta os resultados estaduais com até quatro requisições estaduais simultâneas.

O cache em memória é local a cada processo. Ele não é compartilhado entre várias instâncias da API e é perdido quando o processo reinicia.

Para uma implantação maior, considere um cache compartilhado, como Redis, e mecanismos de controle de concorrência entre consultas iguais.

## Logs

Os logs da aplicação são registrados em JSON.

Entre os eventos disponíveis estão:

- `http_request_completed`: requisição HTTP processada.
- `tse_cache_hit`: resposta encontrada no cache.
- `tse_cache_miss`: resposta não encontrada no cache.
- `tse_request_completed`: consulta ao TSE concluída.
- `tse_request_failed`: falha na consulta ao TSE.
- `tse_invalid_json`: resposta JSON inválida.

Cada requisição HTTP registra informações como método, caminho, código de resposta e duração.

Os logs permitem investigar problemas sem precisar adicionar instruções temporárias de impressão ao código.

## Testes automatizados

Execute toda a suíte de testes com:

```powershell
python -m pytest -v
```

Os testes cobrem:

- Endpoints da FastAPI.
- Validação e normalização de parâmetros.
- Modelos de resultados.
- Tratamento global de exceções.
- Middleware de requisições.
- Configurações.
- Cliente HTTP, erros, logs e cache.
- Parser e regras do repositório eleitoral.

Os testes utilizam respostas simuladas e não precisam consultar o TSE real.

Ao adicionar uma funcionalidade, crie testes correspondentes antes de considerar a implementação concluída.

## Limitações atuais

- O repositório está configurado inicialmente para 2026.
- A consulta por UF e a distribuição de votos por candidato foram implementadas para a Presidência.
- O segundo turno depende da existência dos arquivos oficiais correspondentes no TSE.
- Ainda não há persistência em banco de dados.
- Ainda não há autenticação, autorização ou limitação de requisições para uso público.
- Os clientes Telegram, WhatsApp, Discord e o site ainda não estão implementados.

Não presuma que um arquivo inexistente indica necessariamente ausência de resultados publicados: a URL pode estar incorreta ou ter mudado. A API deve tratar essa situação como indisponibilidade de dados até que a causa seja confirmada.

## Próximas etapas

1. Completar e validar os testes de integração com dados oficiais.
2. Adicionar documentação e exemplos para os modelos de resposta.
3. Avaliar cache compartilhado e persistência, se necessários.
4. Preparar autenticação, limitação de requisições e configuração de produção.
5. Criar um cliente Telegram que consuma a API HTTP.
6. Reutilizar a mesma API para um site, Discord e WhatsApp.

## Princípio arquitetural

A `eleicoes_api` é a fonte central das regras de consulta eleitoral.

Os clientes devem ser responsáveis apenas por receber comandos, chamar a API e apresentar os resultados. Dessa maneira, novos canais podem ser implementados sem duplicar a lógica eleitoral.
